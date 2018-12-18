import pandas as pd
import datetime
import urllib.request
import urllib.error
import base64
import json
import math
import re


class FitbitData:
    def __init__(self):
        super().__init__()
        self.data_type = ''
        self.f_id = ''
        self.fitbit_id = ''
        self.p_id = ''
        self.p_time = ''
        self.start_date = ''
        self.end_date = ''
        self.minute_type = ''
        self.full_id = ''
        self.acc_token = ''
        self.ref_token = ''
        self.valid_dates = []
        self.non_valid_dates = []
        self.different_dates = []
        # 기준 착용기간 (6일 + 여유 5일)
        self.period_criteria = 11
        # get data from fitbit
        self.fitbit_db = pd.read_csv('/Users/sjyoung/PycharmProjects/fitbit_data/data/lung_db.csv', index_col=0)
        self.TokenRefreshedOK = "Token refreshed OK"
        self.ErrorInAPI = "Error when making API call that I couldn't handle"

    # file_path = '/Users/sjyoung/PycharmProjects/pyqt/report/201801_patients_data.csv'
    def read_data_table(self, file_path):
        if self.isBlank(file_path) is True:
            return

        file_type = file_path[-3:]
        if file_type == "csv":
            data_table = pd.read_csv(file_path)
        elif file_type in ["lsx", "xls"]:
            data_table = pd.read_excel(file_path, sheet_name=None)
        else:
            data_table = None

        return data_table

    # 날짜 형식이 유효한지 체크
    def check_valid_date(self, date):
        if self.isBlank(str(date)) is True:
            return "false"

        date_obj = self.get_date_object(date)

        if isinstance(date_obj, datetime.date):
            return "false"

    # 오늘 날짜를 구한다
    def get_today_date(self):
        today_time = datetime.datetime.now()
        today_date = today_time.strftime('%Y%m%d')

        return today_date

    # 분당 데이터의 총합과 daily step 수의 비교
    def validate_step_data(self, date, sum_data):
        # daily step 데이터 얻어와서 dict 형태로 저장
        url = self.get_activity_url("steps", date, date)
        dict_daily_step = self.get_option_data(date, [url], "crf")
        # dict 형태 ex) dict_daily_step = {'2018-01-30': ['1885']}

        if len(dict_daily_step) > 0:
            daily_step = dict_daily_step[date][0]
            if not isinstance(daily_step, float):
                # 비교를 위해 float 형태로 변경
                daily_step = float(daily_step)

            # 분당 데이터 총합과 데일리 데이터가 다르면 different_dates 배열에 추가
            if self.compare_data(daily_step, sum_data) is False:
                data_gap = float(sum_data - daily_step)
                differ_data = [self.full_id, self.f_id, date, sum_data, daily_step, data_gap]
                self.different_dates.append(differ_data)
                print("error report = ", self.full_id, date, sum_data, " != ", daily_step, data_gap)

    def compare_data(self, data, target_data):
        comp_result = False

        if type(data) == type(target_data):
            if data == target_data:
                comp_result = True

        return comp_result

    # 여기에서 데이터 타입별로 분기를 시키자 !!
    def classify_data_type(self, data_type, file_path, save_path, save_name, verify_data):
        df = self.read_data_table(file_path)
        if df is not None:
            for i, row in df.iterrows():
                p_id = row['PID']
                f_id = row['FID']
                p_time = row['Time']
                start_date = row['StartDate']
                end_date = row['EndDate']

                start_date_obj = self.get_date_object(start_date)
                end_date_obj = self.get_date_object(end_date)

                if not isinstance(end_date_obj, datetime.date):
                    print(p_id, "not instance of datetime.date end_date = ", end_date_obj)
                    return

                self.p_id = self.convert_p_id(str(p_id))
                self.f_id = f_id
                self.fitbit_id = self.convert_fitbit_id(f_id)
                self.p_time = int(p_time) if not math.isnan(p_time) else ''
                self.data_type = data_type

                adjusted_dates = self.adjust_dates(start_date_obj, end_date_obj)
                if len(adjusted_dates) == 0:
                    print(self.p_id, "len(adjusted_dates) == 0 end_date = ", end_date_obj)
                    return
                self.start_date = str(adjusted_dates['start_date'])
                self.end_date = str(adjusted_dates['end_date'])

                # get access and reference token
                self.acc_token, self.ref_token = self.get_fitbit_tokens(self.fitbit_id)

                self.non_valid_dates = self.get_non_valid_date()
                self.valid_dates = self.get_valid_dates(self.non_valid_dates)

                # 실제 착용기간(period): 유효날짜 중 첫날 ~ 마지막날
                if len(self.valid_dates) > 0:
                    valid_start_date = self.get_date_object(self.valid_dates[0]).strftime('%Y%m%d')
                    valid_end_date = self.get_date_object(self.valid_dates[len(self.valid_dates) - 1]).strftime(
                        '%Y%m%d')
                    period = valid_start_date + "-" + valid_end_date

                else:
                    period = ''

                # lung001_1차_FL001_20160101_20160120_20160201
                self.full_id = str(self.p_id) + '_' + str(self.p_time) + '차_' + self.f_id + '_' +\
                    start_date_obj.strftime('%Y%m%d') + '_' + end_date_obj.strftime('%Y%m%d') + '_' +\
                    self.get_today_date()

                if self.data_type in ["1min", "15min"]:
                    print("1min, 15min")
                    df_data = self.get_min_data(verify_data)
                    print(df_data)
                    save_name = self.full_id + '_' + self.data_type
                    self.save_data(df_data, save_path, save_name, "excel")

                elif self.data_type == "crf":
                    print("crf")
                    if i == 0:
                        columns = ['id', 'period', 'fitbit_step', 'fitbit_distance', 'fitbit_calories',
                                   'fitbit_activity_calories',
                                   'fitbit_VPA_time', 'fitbit_MPA_time', 'fitbit_LAP_time', 'TAT', 'fitbit_spa_time',
                                   'fitbit_sleep_wakeup_time', 'fitbit_wakeup_fq', 'fitbit_sleep_bed_time',
                                   'fitbit_wear_days', 'non_valid_dates']
                        df_data = pd.DataFrame(columns=columns)

                    list_crf_data = self.get_crf_data()
                    if list_crf_data is not None:
                        print("id = ", self.full_id)
                        print("list crf data = ", [self.full_id] + list_crf_data)
                        df_data.loc[len(df_data)] = [self.full_id, period] + list_crf_data

                    if i == (len(df) - 1):
                        self.save_data(df_data, save_path, save_name, "csv")

                elif self.data_type == "daily":
                    print("daily")
                    df_data = self.get_week_data()
                    save_name = self.full_id + '_' + self.data_type
                    self.save_data(df_data, save_path, save_name, "excel")

            if verify_data is True:
                columns = ["id", "f_id", "date", "sum_data", "daily_data", "gap"]
                df_error_report = pd.DataFrame(self.different_dates, columns=columns)
                writer = pd.ExcelWriter(save_path + '/fitbit_error_report.xlsx')
                df_error_report.to_excel(writer, 'Sheet1', index=False)
                writer.save()

    def save_data(self, df_data, save_path, save_name, save_option):
        # 엑셀로 저장
        if save_option == "excel":
            writer = pd.ExcelWriter(save_path + '/' + save_name + '.xlsx')
            df_data.to_excel(writer, 'Sheet1', index=False)
            writer.save()

        # csv로 저장
        elif save_option == "csv":
            df_data.to_csv(save_path + '/' + save_name + '.csv', index=False)

    # 1min/15min data 얻은 후 csv 파일에 저장
    def get_min_data(self, verify_data):
        date_cal = []
        dict_data_value = dict()

        # day 별 1min data 가져와서 csv 파일에 저장
        for idx, date in enumerate(self.valid_dates):
            date_cal.append(date)
            # url request & response
            fitbit_api_url = "https://api.fitbit.com/1/user/-/activities/steps/date/" + date \
                             + "/1d/" + self.data_type + "/time/00:00/23:59.json"
            fitbit_full_res = self.get_api_response(fitbit_api_url)

            if fitbit_full_res is None:
                print("fitbit_full_res is None")
                return

            # 정규식 패턴 매칭
            if idx == 0:
                time_value = self.get_time_data(fitbit_full_res)
                dict_data_value['time'] = time_value
            fitbit_data = self.get_value_data(fitbit_full_res, "min")
            dict_data_value[date] = fitbit_data

            if verify_data is True:
                # 분당 데이터 총합 구한 후 데일리 데이터와 비교 검증
                sum_value = self.sum_data(fitbit_data)
                self.validate_step_data(date, sum_value)

        df_data_total = pd.DataFrame.from_dict(dict_data_value)
        # time 이 맨 왼쪽열로 오도록 조정
        df_data_total = df_data_total.reindex(columns=(['time']
                                                       + list([a for a in df_data_total.columns if a != 'time'])))

        return df_data_total

    # activity 데이터 URL Path 얻기
    def get_activity_url(self, option, start_date, end_date):
        if self.isBlank(option) is True:
            print("option is blank")
            return ''

        url_front = "https://api.fitbit.com/1/user/-/activities/"
        url_end = "/date/" + start_date + "/" + end_date + ".json"

        return url_front + option + url_end

    def get_activity_list(self, date):
        url_front = "https://api.fitbit.com/1/user/-/activities/date/"
        url_end = date + ".json"

        return url_front + url_end

    # sleep 데이터 URL Path 얻기
    def get_sleep_url(self, start_date, end_date):
        url_front = "https://api.fitbit.com/1.2/user/-/sleep"
        url_end = "/date/" + start_date + "/" + end_date + ".json"

        return url_front + url_end

    def set_crf_data(self, file_path, save_path, save_file_name):
        print("file_path = ", file_path)
        print("save_path = ", save_path)
        print("save_file_name = ", save_file_name)
        df = self.read_data_table(file_path)

        # 20180410 'fitbit_sleep_wakeup_time', 'fitbit_wakeup_fq', 'fitbit_sleep_bed_time' 추가
        columns = ['id', 'fitbit_step', 'fitbit_distance', 'fitbit_calories', 'fitbit_activity_calories',
                   'fitbit_VPA_time', 'fitbit_MPA_time', 'fitbit_LPA_time', 'TAT', 'fitbit_spa_time',
                   'fitbit_sleep_wakeup_time', 'fitbit_wakeup_fq', 'fitbit_sleep_bed_time',
                   'fitbit_wear_days', 'non_valid_dates']
        df_data_total = pd.DataFrame(columns=columns)

        for i, row in df.iterrows():
            p_id = row['PID']
            f_id = row['FID']
            p_time = row['Time']
            start_date = row['StartDate']
            end_date = row['EndDate']

            list_crf_data = self.get_crf_data(p_id, f_id, p_time, start_date, end_date)
            print("list_crf_data = ", list_crf_data)
            if list_crf_data is not None:
                df_data_total.loc[len(df_data_total)] = list_crf_data

        df_data_total.to_csv(save_path + '/' + save_file_name + '.csv', index=False)

    # CRF 데이터 얻기
    def get_crf_data(self):
        list_total_data = []
        total_activity_time = 0

        # 얻고자 하는 정보들의 url list
        data_options = ["steps", "distance", "calories", "activityCalories", "minutesVeryActive",
                        "minutesFairlyActive", "minutesLightlyActive", "minutesSedentary"]
        sleep_options = ["awake_minutes", "awake_count", "time_in_bed"]

        data_options.extend(sleep_options)

        for idx, option in enumerate(data_options):
            valid_values = []

            if option in sleep_options:
                url = self.get_sleep_url(self.start_date, self.end_date)
            else:
                url = self.get_activity_url(option, self.start_date, self.end_date)

            fitbit_full_res = self.get_api_response(url)

            if fitbit_full_res is None:
                print("fitbit response is None")
                return

            # decode 후 json 형태로 변환
            decode_res = fitbit_full_res.decode("utf-8")
            print("decode_res = ", decode_res)
            json_res = json.loads(decode_res.replace("'", "\""))
            print("json_res = ", json_res)

            # 20180410 sleep data 추가
            if option in sleep_options:
                option_value = json_res['sleep']
            else:
                option_value = json_res['activities-' + option]

            # 전체 data 에서 valid date 의 data만 추출
            # sleep data는 valid/non-valid 체크 불필요
            for value in option_value:
                if option in sleep_options:
                    valid_values.append(value)
                else:
                    date_time = value.get('dateTime')
                    if date_time not in self.non_valid_dates:
                        valid_values.append(value)

            if option in sleep_options:
                fitbit_data = self.get_value_data(json.dumps(valid_values), option)

            else:
                fitbit_data = self.get_value_data(json.dumps(valid_values), "crf")

            # 평균 계산
            average_result = self.average_data(fitbit_data)
            average_str = str(average_result)
            list_total_data.append(average_str)

            # TAT(Total Activity Time) 구하기
            if option in ["minutesVeryActive", "minutesFairlyActive", "minutesLightlyActive"]:
                total_activity_time += average_result

                if option == 'minutesLightlyActive':
                    list_total_data.append(str(total_activity_time))

        list_total_data.append(self.get_valid_dates_count(self.non_valid_dates))
        list_total_data.append(self.non_valid_dates)

        return list_total_data

    def get_week_data(self):
        # 얻고자 하는 정보들의 url list
        data_options = ["steps", "distance", "calories", "activityCalories", "minutesVeryActive",
                        "minutesFairlyActive", "minutesLightlyActive", "minutesSedentary"]

        week_data_dict = dict()

        for idx, option in enumerate(data_options):
            valid_values = []

            url = self.get_activity_url(option, self.start_date, self.end_date)
            #url2 = self.get_activity_list(self.start_date)
            #print("URL = ", url2)
            fitbit_full_res = self.get_api_response(url)

            if fitbit_full_res is None:
                print("get_week_data: fitbit_full_res is None")
                return

            # decode 후 json 형태로 변환
            decode_res = fitbit_full_res.decode("utf-8")
            #print("daily data = ", decode_res)

            json_res = json.loads(decode_res.replace("'", "\""))
            option_value = json_res['activities-' + option]

            # 전체 data 에서 valid date 의 data만 추출
            # sleep data는 valid/non-valid 체크 불필요
            for value in option_value:
                date_time = value.get('dateTime')
                if date_time not in self.non_valid_dates:
                    valid_values.append(value)

            # 정규식 패턴 매칭
            if idx == 0:
                week_data_dict['date'] = self.valid_dates
            fitbit_data = self.get_value_data(json.dumps(valid_values), "crf")

            week_data_dict[option] = fitbit_data

        df_week_data = pd.DataFrame.from_dict(week_data_dict)
        data_options.insert(0, 'date')
        df_week_data = df_week_data.reindex(columns=data_options)
        df_week_data.set_index('date')

        return df_week_data

    # ?
    def get_option_data(self, cur_date, url_list, data_type):
        dict_data_value = dict()

        for url in url_list:
            fitbit_res = self.get_api_response(url)

            if fitbit_res is not None:
                if data_type == "crf":
                    decode_res = fitbit_res.decode("utf-8")
                    json_res = json.loads(decode_res.replace("'", "\""))
                    option_value = json_res['activities-' + "steps"]
                    fitbit_res = json.dumps(option_value)
                else:
                    time_value = self.get_time_data(fitbit_res)
                    dict_data_value['time'] = time_value

                fitbit_data = self.get_value_data(fitbit_res, data_type)
                dict_data_value[cur_date] = fitbit_data

        return dict_data_value


    # non_valid_date 구하기
    # 조건 : 4시간동안 fitbit 활동내역이 없으면 non valid date 로 판단
    def get_non_valid_date(self):
        non_valid_dates = []
        valid_dates = []
        dates_list = self.get_valid_dates(non_valid_dates)

        start_time = '08:00:00'
        end_time = '20:00:00'

        # end_date 부터 탐색해서 non_valid_date 일 경우, update_period
        for date in dates_list:
            url = "https://api.fitbit.com/1/user/-/activities/steps/date/" + date + "/1d/15min/time/00:00/23:59.json"
            dict_data_value = self.get_option_data(date, [url], "min")
            df_daily_data = pd.DataFrame.from_dict(dict_data_value)

            if len(df_daily_data) > 0:
                df_daily_data = df_daily_data.set_index(['time'])
                #TODO: np array 활용하는걸로 바꿔보자!
                df_daytime = df_daily_data.loc[start_time:end_time]

                non_active_count = 0
                # 활동량 데이터가 4시간 연속 0 일 경우 non_valid_dates 에 추가
                for i, row in df_daytime.iterrows():
                    if row[date] == '0':
                        non_active_count += 1
                        if non_active_count > 16:
                            non_valid_dates.append(date)
                            break
                    else:
                        non_active_count = 0

                valid_dates.append(date)

        print("non_valid_dates = ", non_valid_dates)
        return non_valid_dates

    # valid dates 개수 구하기
    def get_valid_dates_count(self, non_valid_dates):
        start_day = self.get_date_object(self.start_date)
        end_day = self.get_date_object(self.end_date)

        day_count = (end_day - start_day).days + 1

        return day_count - len(non_valid_dates)

    # non_valid_dates 를 제외한 valid dates 를 리스트 형태로 가져오기
    def get_valid_dates(self, non_valid_dates):
        valid_dates = []

        start_day = self.get_date_object(self.start_date)
        end_day = self.get_date_object(self.end_date)

        day_count = (end_day - start_day).days + 1

        for i in range(day_count):
            cur_date = (start_day + datetime.timedelta(i)).strftime('%Y-%m-%d')
            if cur_date not in non_valid_dates:
                valid_dates.append(cur_date)

        print("valid_dates = ", valid_dates)
        print("valid_dates_count = ", len(valid_dates))
        return valid_dates

    # fitbit_db 에서 token 값 가져오기
    def get_fitbit_tokens(self, fitbit_id):
        ref_token = self.fitbit_db.ix[fitbit_id]['ref_token']
        self.GetNewAccessToken(fitbit_id, ref_token)
        acc_token = self.fitbit_db.ix[fitbit_id]['acc_token']
        ref_token = self.fitbit_db.ix[fitbit_id]['ref_token']

        return acc_token, ref_token

    # url 을 넘겨받아 request 보낸 후 response 값을 반환한다
    def get_api_response(self, fitbit_api_url):
        try:
            fitbit_req = urllib.request.Request(fitbit_api_url)
            fitbit_req.add_header('Authorization', 'Bearer ' + self.acc_token)

            fitbit_res = urllib.request.urlopen(fitbit_req)
            fitbit_full_res = fitbit_res.read()

            return fitbit_full_res

        except urllib.error.HTTPError as e:
            print("Got this HTTP error: " + str(e.reason))
            print("This was in the HTTP error message: " + str(e.code))
            print("patient id = ", self.p_id, "fitbit id = ", self.f_id)
            # See what the error was
            if e.code == 401:
                self.GetNewAccessToken(self.ref_token)
                print('Error code: 401 Try again! ')
                #sys.exit()
                pass
            elif e.code == 429:
                print('Error code: 429 Too Many Requests! Try again after 1 hour.. ')
                #sys.exit()
                pass

    # 정규식을 이용해 time 값을 찾아 반환한다
    def get_time_data(self, fitbit_res):
        time_pattern = re.compile('\d+:\d+:\d+')
        time_value = time_pattern.findall(fitbit_res.decode("utf-8"))

        return time_value

    # 정규식을 이용해 dateTime 값을 찾아 반환한다
    def get_datetime_data(self, fitbit_res):
        date_pattern = re.compile('"dateTime":"\d+')
        date_value = date_pattern.findall(fitbit_res.decode("utf-8"))

        return date_value

    # 정규식을 이용해 value 값을 찾아 반환한다
    def get_value_data(self, fitbit_res, data_type):
        if self.isBlank(data_type) is True:
            print("get_value_data: data_type is blank")
            return []

        value_pattern = ''

        if data_type == "min":
            value_pattern = re.compile('"value":\d+')

        elif data_type == "crf":
            value_pattern = re.compile('"value": "\d*\.?\d+"')

        elif data_type == "time_in_bed":
            value_pattern = re.compile('"timeInBed": \d+')

        elif data_type in ["awake_count", "awake_minutes"]:
            awake_type = data_type.split("_")[1]
            awake_pattern = re.compile('"awake": \{[^{}]*')
            fitbit_res = str(awake_pattern.findall(fitbit_res))
            value_pattern = re.compile('"' + awake_type + '": \d+')

        number_pattern = re.compile('\d*\.?\d+')

        if isinstance(fitbit_res, list):
            fitbit_res = json.dumps(fitbit_res)
        elif isinstance(fitbit_res, bytes):
            fitbit_res = fitbit_res.decode("utf-8")

        fitbit_value = value_pattern.findall(fitbit_res)
        fitbit_data = number_pattern.findall(str(fitbit_value))

        return fitbit_data

    def get_sleep_value(self, fitbit_res):
        time_bed_pattern = re.compile('"timeInBed": \d+')
        awake_pattern = re.compile('"awake": \{[^{}]*')
        count_pattern = re.compile('"count": \d+')
        minute_pattern = re.compile('"minutes": \d+')

        number_pattern = re.compile('\d+')

        # time in bed
        time_bed_value = time_bed_pattern.findall(fitbit_res)
        time_bed_num = number_pattern.findall(str(time_bed_value))

        # awake time & count
        awake_value = awake_pattern.findall(fitbit_res)
        awake_time = minute_pattern.findall(str(awake_value))
        awake_time_num = number_pattern.findall(str(awake_time))
        awake_count = count_pattern.findall(str(awake_value))
        awake_count_num = number_pattern.findall(str(awake_count))

        return {"time_in_bed": time_bed_num, "awake_time": awake_time_num, "awake_count": awake_count_num}

    # data list 들의 평균값 구하기
    def average_data(self, data_list):
        sum_value = self.sum_data(data_list)
        if sum_value > 0:
            average = sum_value / len(data_list)
        else:
            average = 0

        # 반올림이 필요하면 --> round(average, 2)
        return round(average, 2) if average > 0 else average

    # data list 들의 총합 구하기
    def sum_data(self, data_list):
        return sum(float(data) for data in data_list)

    # fitbit id 형식 변환 'FE001' -> 'ego001'
    def convert_fitbit_id(self, f_id):
        if self.isBlank(f_id) is True:
            print("convert_fitbit_id: f_id is blank")
            return ''

        fitbit_id = ''
        cancer_type = f_id[1:2]

        if cancer_type == 'E':
            fitbit_id = 'ego' + f_id[2:5]
        elif cancer_type == 'L':
            fitbit_id = 'lung' + f_id[2:5]
        else:
            fitbit_id = f_id

        return fitbit_id

    # patient id 형식 변환
    def convert_p_id(self, p_id):
        if self.isBlank(p_id) is True:
            print("convert_p_id: p_id is blank")
            return ''

        # 공백 제거
        p_id = p_id.strip()

        if self.isNumber(p_id):
            patient_id = 'lung' + str(p_id).zfill(3)
        else:
            patient_id = p_id

        return patient_id

    # 숫자이면 true, 숫자가 아니면 false
    def isNumber(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    # 공백 또는 NULL 이면 true
    def isBlank(self, string):
        return not (string and string.strip())

    # 유효한 날짜 조정
    def adjust_dates(self, start_date_obj, end_date_obj):
        if not (isinstance(start_date_obj, datetime.date) and isinstance(end_date_obj, datetime.date)):
            print("adjust_dates: startDate or endDate is not instance of datetime.date")
            return {}

        # 착용한 날짜와 회수된 날짜의 차이
        delta_days = (end_date_obj - start_date_obj).days

        # 착용 첫날 제외
        start_date = self.add_date(start_date_obj, 1)

        if delta_days > 0:
            if delta_days > self.period_criteria:
                # 11 - 17
                end_date = self.add_date(end_date_obj, self.period_criteria - delta_days)
                print("original endDate = ", end_date_obj, "delta = ", delta_days, "adjusted endDate = ", end_date)

            else:
                # 착용 마지막날(회수날) 제외
                end_date = self.add_date(end_date_obj, -1)
        else:
            # 날짜 차이가 0보다 같거나 작은 경우
            print("delta_days(end_date - start_date) <= 0")
            return {}

        return {'start_date': start_date, 'end_date': end_date}

    # end date 조정
    def adjust_end_date(self, start_date_obj, end_date_obj):
        if not (isinstance(start_date_obj, datetime.date) and isinstance(end_date_obj, datetime.date)):
            print("adjust_end_date: startDate, endDate is not instance of datetime.date")
            return self.end_date

        # 날짜 계산 : end_date - start_date 계산해서 7일 이상인 경우 -- / 7일 이하인 경우 ++
        delta = start_date_obj - end_date_obj
        delta_days = delta.days
        if delta != 0:
            # 날짜 간격이 7일이 되도록 수정한 후, 5일 추가
            end_date = self.add_date(end_date_obj, add_value=delta_days + 7 + 5)

        return end_date

    # date 객체 생성
    def get_date_object(self, date, sep="-"):
        #TODO: date 값이 제대로 들어왔는지 체크
        date = str(date)
        separated_date = date.split(sep)
        # separated_date 가 공백이면 sep="." 으로 다시 수행
        if len(separated_date) < 2:
            sep = "."
            separated_date = date.split(sep)

        try:
            year = int(separated_date[0])
            month = int(separated_date[1])
            day = int(separated_date[2])
            date_obj = datetime.date(year, month, day)
        except ValueError:
            date_obj = ''

        return date_obj

    # add_value 만큼 날짜 더하기
    def add_date(self, date_obj, add_value):
        return date_obj + datetime.timedelta(days=add_value)

    # 새로운 AccessToken 받기
    def GetNewAccessToken(self, f_id, RefToken):
        # Form the data payload
        BodyText = {'grant_type': 'refresh_token',
                        'refresh_token': RefToken}
        # URL Encode it
        BodyURLEncoded = urllib.parse.urlencode(BodyText)
        # Start the request
        TokenURL = "https://api.fitbit.com/oauth2/token"
        tokenreq = urllib.request.Request(TokenURL, BodyURLEncoded.encode('utf-8'))

        OAuthTwoClientID = self.fitbit_db.ix[f_id]['client_ID']
        ClientOrConsumerSecret = self.fitbit_db.ix[f_id]['client_sec']
        RedirectURL = self.fitbit_db.ix[f_id]['redirect_url']

        sen = (OAuthTwoClientID + ":" + ClientOrConsumerSecret)
        sentence = base64.b64encode(sen.encode('utf-8'))

        tokenreq.add_header('Authorization', 'Basic ' + sentence.decode('utf-8'))
        tokenreq.add_header('Content-Type', 'application/x-www-form-urlencoded')

        # Fire off the request
        try:
            tokenresponse = urllib.request.urlopen(tokenreq)

            # See what we got back.  If it's this part of  the code it was OK
            self.FullResponse = tokenresponse.read()

            # Need to pick out the access token and write it to the config file.  Use a JSON manipluation module
            ResponseJSON = json.loads(self.FullResponse)

            # Read the access token as a string
            NewAccessToken = str(ResponseJSON['access_token'])
            NewRefreshToken = str(ResponseJSON['refresh_token'])
            # Write the access token to the ini file

            self.fitbit_db.ix[f_id]['acc_token'] = NewAccessToken
            self.fitbit_db.ix[f_id]['ref_token'] = NewRefreshToken

            self.fitbit_db.to_csv('/Users/sjyoung/PycharmProjects/fitbit_data/data/lung_db.csv')

        except urllib.error.HTTPError as e:
            # Gettin to this part of the code means we got an error
            print("An error was raised when getting the access token. Need to stop here -", self.p_id)
            print(e.reason)
            pass
            #sys.exit()