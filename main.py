import re
import sqlite3
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

Builder.load_file("opt.kv")


class UpperCaseTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        # Use regular expression to match only English letters (a-z, A-Z)
        filtered_text = re.sub(r'[^a-zA-Z]', '', substring)
        new_text = filtered_text.upper()
        return super(UpperCaseTextInput, self).insert_text(new_text, from_undo=from_undo)

class NumericTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        # Filter out non-numeric characters and allow the minus sign for negative numbers
        if substring == "-" and not self.text:
            return super(NumericTextInput, self).insert_text(substring, from_undo=from_undo)
        elif (substring.startswith("-") and substring[1:].isdigit()) or substring.isdigit():
            return super(NumericTextInput, self).insert_text(substring, from_undo=from_undo)
        return False


class MyBoxLayout(BoxLayout):
    def __init__(self, cursor, **kwargs):
        super().__init__(**kwargs)
        self.cursor = cursor


    TEMPERATURES_FLAPS15 = [-50, -40, -30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
    TEMPERATURES_FLAPS5 = [-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]


    def find_temperature_range_flaps(self, temperature, flap_setting):
        lower_temp_index = None
        upper_temp_index = None
        if flap_setting == 'Flaps 15':
            temperatures = self.TEMPERATURES_FLAPS15
        elif flap_setting == 'Flaps 5':
            temperatures = self.TEMPERATURES_FLAPS5
        else:
            self.ids.label.text = "Invalid flap setting."
            return

        for i in range(len(temperatures) - 1):
            if temperatures[i] <= temperature < temperatures[i + 1]:
                if flap_setting == 'Flaps 15':
                    lower_temp_index = i
                    upper_temp_index = i + 1
                else:
                    lower_temp_index = i - 1 if i > 0 else i
                    upper_temp_index = i
                print(f"{flap_setting} lower_temp_index:{lower_temp_index} upper_temp_index:{upper_temp_index}")
                return lower_temp_index, upper_temp_index
        return lower_temp_index, upper_temp_index

    @staticmethod
    def pressure_altitude_range(number):
        lower_alt = (number // 100) * 100
        upper_alt = ((number + 99) // 100) * 100
        return lower_alt, upper_alt

    def on_text_change(self, instance, value):
        if len(value) > 4:
            instance.text = value[:4]

    def btn_pressed(self):
        QNH_text = self.ids.qnh.text
        if QNH_text:
            QNH = int(QNH_text)
            DELTA_hPa = 1013 - QNH
        else:
            DELTA_hPa = 0

        APT_ID = self.ids.airport.text
        query = "SELECT * FROM airports WHERE ICAO = ?"
        self.cursor.execute(query, (APT_ID,))
        result = self.cursor.fetchone()
        if result is not None:
            DELTA_m = DELTA_hPa * 8
            ALTITUDE_METERS = result[10] * 0.3048
            INFO = f"Аэропорт: {result[5]}\nГород: {result[6]},\nPressure Altitude: {int(ALTITUDE_METERS) + DELTA_m}"
            PRESSURE_ALTITUDE = ALTITUDE_METERS + DELTA_m
        else:
            INFO = "Нет данных для указанного аэропорта"
            PRESSURE_ALTITUDE = 0

        temperature_text = self.ids.temperature.text
        if temperature_text:
            TEMPERATURE = int(temperature_text)
        else:
            TEMPERATURE = 15

        flap_setting = self.ids.flap_spinner.text
        if flap_setting == 'Flaps 15':
            TEMPERATURES = self.TEMPERATURES_FLAPS15
            table_name = 'F15OPT'
        elif flap_setting == 'Flaps 5':
            TEMPERATURES = self.TEMPERATURES_FLAPS5
            table_name = 'F5OPT'
        else:
            self.ids.label.text = "Invalid flap setting."
            return


        lower_temp_index, upper_temp_index = self.find_temperature_range_flaps(TEMPERATURE, flap_setting)
        if lower_temp_index is None or upper_temp_index is None:
            self.ids.label.text = "Температура за пределами значений"
            return

        lower, upper = self.pressure_altitude_range(PRESSURE_ALTITUDE)
        query = f"SELECT * FROM {table_name} WHERE pr_alt BETWEEN ? AND ?"
        self.cursor.execute(query, (lower, upper))
        MTOW_ROWS = self.cursor.fetchall()
        MTOW_LOWER = None
        MTOW_UPPER = None
        for row in MTOW_ROWS:
            pr_alt_value = row[0]
            if pr_alt_value == lower:
                MTOW_LOWER = row
            elif pr_alt_value == upper:
                MTOW_UPPER = row

        if MTOW_LOWER is None or MTOW_UPPER is None:
            self.ids.label.text = "Нет данных для указанного аэропорта"
            return

        ALT_FACTOR = (PRESSURE_ALTITUDE - lower) / 100
        MTOW_LOW_TEMPT = int(MTOW_LOWER[lower_temp_index + 1] - ((MTOW_LOWER[lower_temp_index + 1] - MTOW_UPPER[lower_temp_index +1]) * ALT_FACTOR))
        MTOW_UPPER_TEMPT = int(MTOW_LOWER[upper_temp_index + 1] - ((MTOW_LOWER[upper_temp_index + 1] - MTOW_UPPER[upper_temp_index +1]) * ALT_FACTOR))
        DELTA_T_MEASURED = TEMPERATURE - TEMPERATURES[lower_temp_index]
        DELTA_T_SCALE = TEMPERATURES[upper_temp_index] - TEMPERATURES[lower_temp_index]
        TEMPERATURE_FACTOR = ((MTOW_LOW_TEMPT - MTOW_UPPER_TEMPT) / DELTA_T_SCALE) * DELTA_T_MEASURED
        MTOW = MTOW_LOW_TEMPT - TEMPERATURE_FACTOR
        print(f"высота {PRESSURE_ALTITUDE}, диапазон: {lower} - {upper},\nТемература: {TEMPERATURE}")
        print(f"{MTOW_LOWER[lower_temp_index + 1]} - {MTOW_LOWER[upper_temp_index + 1]}")
        print(f"MTOW по фактической высоте: {MTOW_LOW_TEMPT} - {MTOW_UPPER_TEMPT}")
        print(f"{MTOW_UPPER[lower_temp_index +1]} - {MTOW_UPPER[upper_temp_index +1]}")
        print(f"MTOW: {MTOW}")

        INFO_FINAL = f"{INFO} MTOW:{int(MTOW)}"
        self.ids.label.text = INFO_FINAL

    def on_spinner_select(self, spinner, text):
        self.ids.label.text = f"{text}"
        print("Selected option:", text)


class MyApp(App):
    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect('apt.db')
        self.cursor = self.conn.cursor()

    def build(self):
        box_layout = MyBoxLayout(cursor=self.cursor)
        return box_layout


if __name__ == '__main__':
    MyApp().run()
