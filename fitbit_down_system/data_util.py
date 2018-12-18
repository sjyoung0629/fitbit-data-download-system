import pandas as pd
import datetime


class DataUtil:
    def __init__(self):
        # 기준 착용기간 (6일 + 여유 5일)
        self.period_criteria = 11

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

    def get_date_object(self, date, sep="-"):
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

    # add_value 만큼 날짜 더하기
    def add_date(self, date_obj, add_value):
        return date_obj + datetime.timedelta(days=add_value)

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
