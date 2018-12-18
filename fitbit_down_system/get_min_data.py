import pandas as pd
import math
import datetime
import urllib.request
import urllib.error
import base64
import json
import re
import os

from fitbit.data_util import DataUtil
from fitbit.step_chart import StepChart
from fitbit.data_manager import DataManager

data_util = DataUtil()
chart = StepChart()
dm = DataManager()


class MinData:
    def __init__(self):
        self.data_type = ''
        self.f_id = ''
        self.fitbit_id = ''
        self.p_id = ''
        self.p_time = ''
        self.start_date = ''
        self.end_date = ''
        self.acc_token = ''
        self.ref_token = ''
        self.valid_dates = []
        self.non_valid_dates = []
        self.fitbit_db = pd.read_csv('/Users/sjyoung/PycharmProjects/fitbit_data/data/lung_db.csv', index_col=0)
        self.TokenRefreshedOK = "Token refreshed OK"

    def get_data(self, p_id, time, f_id, start_date, end_date):
        data = None
        # 해당 폴더 내 파일 탐색
        dir_name = 'fitbit/data'
        file_names = os.listdir(dir_name)
        for filename in file_names:
            print("cur filename = ", filename)
            fn_arr = filename.split('_')
            patient_id = fn_arr[0]
            print("patient_id : ", patient_id, " == ", p_id, patient_id == p_id)
            patient_time = re.findall('\d+', fn_arr[1])
            if len(patient_time) > 0:
                patient_time = patient_time[0]
            print("patient_time : ", patient_time, " == ", time, patient_time == str(time))
            fitbit_id = fn_arr[2]
            print("fitbit_id : ", fitbit_id, " == ", f_id, fitbit_id == f_id)
            if patient_id == p_id and patient_time == str(time) and fitbit_id == f_id:
                full_path = os.path.join(dir_name, filename)
                data = dm.read_data_table(full_path, index_col=0)
                break

        if data is None:
            data = self.get_min_data(p_id, f_id, time, start_date, end_date)

        return data

    def get_time(self, p_id):
        times = []
        # 해당 폴더 내 파일 탐색
        dir_name = 'fitbit/data'
        file_names = os.listdir(dir_name)
        for filename in file_names:
            print("cur filename = ", filename)
            fn_arr = filename.split('_')
            patient_id = fn_arr[0]
            if patient_id == p_id:
                patient_time = re.findall('\d+', fn_arr[1])
                if len(patient_time) > 0:
                    patient_time = patient_time[0]

                times.append(patient_time)

        return times

    def get_min_data(self, p_id, f_id, time, start_date, end_date):
        start_date_obj = data_util.get_date_object(start_date)
        end_date_obj = data_util.get_date_object(end_date)

        if not isinstance(end_date_obj, datetime.date):
            print(p_id, "not instance of datetime.date end_date = ", end_date_obj)
            return

        self.p_id = data_util.convert_p_id(str(p_id))
        self.f_id = f_id
        self.fitbit_id = data_util.convert_fitbit_id(f_id)
        self.p_time = int(time) if not math.isnan(time) else ''

        adjusted_dates = data_util.adjust_dates(start_date_obj, end_date_obj)
        if len(adjusted_dates) == 0:
            print(self.p_id, "len(adjusted_dates) == 0 end_date = ", end_date_obj)
            return
        self.start_date = str(adjusted_dates['start_date'])
        self.end_date = str(adjusted_dates['end_date'])

        # get access and reference token
        self.acc_token, self.ref_token = self.get_fitbit_tokens(self.fitbit_id)

        self.non_valid_dates = self.get_non_valid_date()
        self.valid_dates = self.get_valid_dates(self.non_valid_dates)

        date_cal = []
        dict_data_value = dict()

        # day 별 1min data 가져와서 csv 파일에 저장
        for idx, date in enumerate(self.valid_dates):
            date_cal.append(date)
            # url request & response
            fitbit_api_url = "https://api.fitbit.com/1/user/-/activities/steps/date/" + date \
                             + "/1d/15min/time/00:00/23:59.json"
            fitbit_full_res = self.get_api_response(self.acc_token, self.ref_token, fitbit_api_url)

            if fitbit_full_res is None:
                print("fitbit_full_res is None")
                return

            # 정규식 패턴 매칭
            if idx == 0:
                time_value = self.get_time_data(fitbit_full_res)
                dict_data_value['time'] = time_value
            fitbit_data = self.get_value_data(fitbit_full_res, "min")
            dict_data_value[date] = fitbit_data

        df_data_total = pd.DataFrame(dict_data_value)
        # 'time'을 index로 지정
        df_data_total = df_data_total.set_index("time")

        return df_data_total

    # non_valid_dates 를 제외한 valid dates 를 리스트 형태로 가져오기
    def get_valid_dates(self, non_valid_dates):
        valid_dates = []

        start_day = data_util.get_date_object(self.start_date)
        end_day = data_util.get_date_object(self.end_date)

        day_count = (end_day - start_day).days + 1

        for i in range(day_count):
            cur_date = (start_day + datetime.timedelta(i)).strftime('%Y-%m-%d')
            if cur_date not in non_valid_dates:
                valid_dates.append(cur_date)

        print("valid_dates = ", valid_dates)
        print("valid_dates_count = ", len(valid_dates))
        return valid_dates

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
        if data_util.isBlank(data_type) is True:
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

    def get_option_data(self, cur_date, url_list, data_type):
        dict_data_value = dict()

        for url in url_list:
            fitbit_res = self.get_api_response(self.acc_token, self.ref_token, url)

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

    def get_api_response(self, acc_token, ref_token, fitbit_api_url):
        try:
            fitbit_req = urllib.request.Request(fitbit_api_url)
            fitbit_req.add_header('Authorization', 'Bearer ' + acc_token)

            fitbit_res = urllib.request.urlopen(fitbit_req)
            fitbit_full_res = fitbit_res.read()

            return fitbit_full_res

        except urllib.error.HTTPError as e:
            print("Got this HTTP error: " + str(e.reason))
            print("This was in the HTTP error message: " + str(e.code))
            print("patient id = ", self.p_id, "fitbit id = ", self.f_id)
            # See what the error was
            if e.code == 401:
                self.GetNewAccessToken(ref_token)
                print('Error code: 401 Try again! ')
                #sys.exit()
                pass
            elif e.code == 429:
                print('Error code: 429 Too Many Requests! Try again after 1 hour.. ')
                #sys.exit()
                pass

    def get_fitbit_tokens(self, fitbit_id):
        ref_token = self.fitbit_db.ix[fitbit_id]['ref_token']
        self.GetNewAccessToken(fitbit_id, ref_token)
        acc_token = self.fitbit_db.ix[fitbit_id]['acc_token']
        ref_token = self.fitbit_db.ix[fitbit_id]['ref_token']

        return acc_token, ref_token

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