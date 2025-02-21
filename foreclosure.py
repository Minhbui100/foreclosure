# UI COMPONENTS
TEXTBOX_DOCUMENT = {}
RB_DATE_TYPE = {
    'sale_date': 'input#ctl00_ContentPlaceHolder1_rbtlDate_0',
    'file_date': 'input#ctl00_ContentPlaceHolder1_rbtlDate_1'
}
DROPDOWN_DATE = {
    'year': 'select#ctl00_ContentPlaceHolder1_ddlYear',
    'month': 'select#ctl00_ContentPlaceHolder1_ddlMonth'
}
BUTTON_SEARCH = 'input#ctl00_ContentPlaceHolder1_btnSearch'
BUTTON_CLEAR = 'input#ctl00_ContentPlaceHolder1_btnClear'

# TEXTS
INFO_MAX_DATE = 'span#ctl00_ContentPlaceHolder1_lblMaxDate'   # Text info on date range available in db

class Foreclosure:
    def __init__(self):
        pass

    def select_date_type_radio_btn(self, date_type):
        pass