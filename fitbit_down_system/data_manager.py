import pandas as pd


# data 관리를 위한 Class
class DataManager():
    def __init__(self):
        super().__init__()

    # file_path = '/Users/sjyoung/PycharmProjects/pyqt/report/201801_patients_data.csv'
    def read_data_table(self, file_path, index_col):
        file_type = file_path[-3:]
        if file_type == "csv":
            data_table = pd.read_csv(file_path, index_col=index_col)
        elif file_type in ["lsx", "xls"]:
            data_table = pd.read_excel(file_path, index_col=index_col)
        else:
            data_table = None

        return data_table

    def save_data(self, df_data, save_path, save_option):
        file_type = save_path[-3:]

        if file_type not in ["csv", "lsx", "xls"]:
            save_path += "." + save_option

        # 엑셀로 저장
        if save_option == "xlsx":
            writer = pd.ExcelWriter(save_path)
            df_data.to_excel(writer, 'Sheet1', index=False)
            writer.save()

        # csv로 저장
        elif save_option == "csv":
            df_data.to_csv(save_path, index=False)
