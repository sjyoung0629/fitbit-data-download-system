import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime


class StepChart:
    def __init__(self):
        super().__init__()
        self.start_time = ':00:00'
        self.end_time = ':45:00'
        self.total_arr = []

    def show_data(self, data, p_id, time):
        df_total = self.get_dataframe(data)
        x = df_total['time']
        y = df_total['date']
        step = df_total['step']
        colors = df_total['color']
        self.scatter(p_id, time, x, y, step, colors)

    # 분당데이터를 불러와서 시각화를 위한 데이터로 만들기
    def get_dataframe(self, data):
        column_values = list(data)
        total_arr = []

        for date in column_values:
            day_data = data[date]

            # date format 변경: 2018/01/01
            format_date = self.change_date_format(date)
            print("after changing format date = ", format_date[2:])
            if format_date is None:
                continue
            else:
                # 18/01/01 형태로 만듦
                format_date = format_date[2:]

            for i in range(24):
                i = str(i)
                if len(i) < 2:
                    i = '0' + i

                # 시간 단위로 데이터 추출
                start_time = i + self.start_time
                end_time = i + self.end_time
                hour_step = day_data.loc[start_time:end_time]
                # int 형변환 후 총합을 구함
                int_hour_step = hour_step.astype(int)
                total_step = int_hour_step.sum()

                # 그래프에 활용하기 위해 10 으로 나눠줌
                preq = total_step / 10
                color = self.get_color(preq)

                # dataframe 생성을 위한 array
                arr = [format_date, i, preq, color]
                total_arr.append(arr)

        df_total = pd.DataFrame(total_arr, columns=['date', 'time', 'step', 'color'])
        return df_total

    # 시각화
    def scatter(self, p_id, time, x, y, size, colors):
        plt.scatter(x, y, s=size, marker='o', color=colors)

        # title 및 label 설정
        self.set_title_label(p_id + ' ' + str(time) + ' - Fitbit Hour-by-Hour', 'hours', 'date')
        plt.xticks(np.arange(0, 24, 1))
        plt.show()

    def set_title_label(self, title, x_label, y_label):
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)

    # datetime 포맷을 '%Y/%m/%d' 로 변경
    def change_date_format(self, date):
        t = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        if isinstance(date, datetime.date):
            date_time = date
        else:
            date_time = datetime.datetime.strptime(date, '%Y-%m-%d')

        day = date_time.weekday()
        print("date = ", date_time, "day = ", day)

        date_time = date_time.strftime('%Y/%m/%d') + ' ' + t[day]

        return date_time

    # 값의 범위에 따라 다른 색상 설정
    # 범위 및 색상은 변경 가능
    def get_color(self, data):
        if data > 200:
            color = '#b72b34'
        elif data > 100:
            color = '#f89f4b'
        elif data > 50:
            color = '#cec64a'
        else:
            color = '#43ad29'

        return color
