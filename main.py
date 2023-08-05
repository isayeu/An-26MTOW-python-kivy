import re
import math
import sqlite3
import numpy as np
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel

Builder.load_file("opt.kv")

class UpperCaseTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        filtered_text = re.sub(r'[^a-zA-Z]', '', substring)
        new_text = filtered_text.upper()
        return super(UpperCaseTextInput, self).insert_text(new_text, from_undo=from_undo)

class NumericTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        if substring == "-" and not self.text:
            return super(NumericTextInput, self).insert_text(substring, from_undo=from_undo)
        elif (substring.startswith("-") and substring[1:].isdigit()) or substring.isdigit():
            return super(NumericTextInput, self).insert_text(substring, from_undo=from_undo)
        return False

class MyBoxLayout(BoxLayout):  # Change the inheritance here
    def __init__(self, cursor, **kwargs):
        super().__init__(**kwargs)
        self.cursor = cursor
        self.TEMPERATURES_FLAPS15 = [-50, -40, -30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
        self.TEMPERATURES_FLAPS5 = [-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
        self.CALM_FLAPS15 = [17000, 25000]
        self.HEADWIND_30_FLAPS15 = [17700, 26069]
        self.CALM_FLAPS5 = [18000, 25000]
        self.HEADWIND_30_FLAPS5 = [18750, 26041]
        self.TAILWIND_5_FLAPS5 = [17750, 24458]

    def find_temperature_range_flaps(self, temperature, flap_setting):
        temperatures = self.TEMPERATURES_FLAPS15 if flap_setting == 'Flaps 15' else self.TEMPERATURES_FLAPS5
        for i, temp in enumerate(temperatures[:-1]):
            if temp <= temperature < temperatures[i + 1]:
                lower_temp_index = i if flap_setting == 'Flaps 5' else i - 1 if i > 0 else i
                upper_temp_index = i + 1
                return lower_temp_index, upper_temp_index
        return None, None

    def pressure_altitude_range(self, number):
        lower_alt = (number // 100) * 100
        upper_alt = ((number + 99) // 100) * 100
        return lower_alt, upper_alt

    def on_text_change(self, instance, value):
        instance.text = value[:4] if len(value) > 4 else value

    def calculate_delta_hPa(self):
        QNH_text = self.ids.qnh.text
        return 1013 - int(QNH_text) if QNH_text else 0

    def calculate_wind_type_and_angle(self, TO_heading, wind_direction):
        wind_angle = (wind_direction - TO_heading) % 360
        if wind_angle <= 180:
            wind_type = "Headwind" if wind_angle <= 89 else "Tailwind"
            wind_angle = 180 - wind_angle
        else:
            wind_type = "Headwind" if wind_angle >= 271 else "Tailwind"
            wind_angle = wind_angle - 180
        return wind_angle, wind_type

    def calculate_headwind_component(self, wind_speed, wind_angle_radians):
        return wind_speed * abs(math.cos(wind_angle_radians))

    def get_heading(self, heading_text):
        try:
            return int(heading_text)
        except ValueError:
            return 0

    def calc_mtow_button(self):
        DELTA_hPa = self.calculate_delta_hPa()
        TO_heading = self.get_heading(self.ids.rw_heading.text)
        wind_direction = int(self.ids.wind_direction.text) if self.ids.wind_direction.text else 0
        wind_speed = int(self.ids.wind_speed.text) if self.ids.wind_speed.text else 0

        wind_angle, wind_type = self.calculate_wind_type_and_angle(TO_heading, wind_direction)
        wind_angle_radians = math.radians(wind_angle)
        headwind_component = self.calculate_headwind_component(wind_speed, wind_angle_radians)

        APT_ID = self.ids.airport.text
        query = "SELECT * FROM airports WHERE ICAO = ?"
        self.cursor.execute(query, (APT_ID,))
        result = self.cursor.fetchone()

        if result:
            DELTA_m = DELTA_hPa * 8
            ALTITUDE_METERS = result[10] * 0.3048
            INFO = f"Аэропорт: {result[5]}\nГород: {result[6]},\nPressure Altitude: {int(ALTITUDE_METERS) + DELTA_m}"
            PRESSURE_ALTITUDE = ALTITUDE_METERS + DELTA_m
        else:
            INFO = "Нет данных для указанного аэропорта"
            PRESSURE_ALTITUDE = 0

        temperature_text = self.ids.temperature.text
        TEMPERATURE = int(temperature_text) if temperature_text else 15

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

        MTOW_LOWER = next((row for row in MTOW_ROWS if row[0] == lower), None)
        MTOW_UPPER = next((row for row in MTOW_ROWS if row[0] == upper), None)

        if MTOW_LOWER is None or MTOW_UPPER is None:
            self.ids.label.text = "Нет данных для указанного аэропорта"
            return

        ALT_FACTOR = (PRESSURE_ALTITUDE - lower) / 100
        MTOW_LOW_TEMPT = int(MTOW_LOWER[lower_temp_index + 1] - ((MTOW_LOWER[lower_temp_index + 1] - MTOW_UPPER[lower_temp_index + 1]) * ALT_FACTOR))
        MTOW_UPPER_TEMPT = int(MTOW_LOWER[upper_temp_index + 1] - ((MTOW_LOWER[upper_temp_index + 1] - MTOW_UPPER[upper_temp_index + 1]) * ALT_FACTOR))
        DELTA_T_MEASURED = TEMPERATURE - TEMPERATURES[lower_temp_index]
        DELTA_T_SCALE = TEMPERATURES[upper_temp_index] - TEMPERATURES[lower_temp_index]
        TEMPERATURE_FACTOR = ((MTOW_LOW_TEMPT - MTOW_UPPER_TEMPT) / DELTA_T_SCALE) * DELTA_T_MEASURED
        CALM_MTOW = MTOW_LOW_TEMPT - TEMPERATURE_FACTOR

        MTOW = self.calculate_final_mtow(CALM_MTOW, flap_setting, wind_type, headwind_component)
        INFO_FINAL = f"{INFO}\n{wind_type}: {round(headwind_component, 2)}\nMTOW:{int(MTOW)}"
        self.ids.label.text = INFO_FINAL
        self.ids.tab2_label_mtow.text = f"MTOW: {str(int(MTOW))}"

    def flaps_spinner_select(self, spinner, text):
        self.ids.label.text = f"{text}"
        print("Selected option:", text)

    def calculate_final_mtow(self, CALM_MTOW, flap_setting, wind_type, headwind_component):
        if flap_setting == 'Flaps 15':
            if wind_type == 'Headwind':
                WIND_FACTOR = ((np.interp(CALM_MTOW, self.CALM_FLAPS15, self.HEADWIND_30_FLAPS15) - CALM_MTOW) / 30) * headwind_component
            else:
                WIND_FACTOR = 100 * headwind_component
        else:
            if wind_type == 'Headwind':
                WIND_FACTOR = ((np.interp(CALM_MTOW, self.CALM_FLAPS5, self.HEADWIND_30_FLAPS5) - CALM_MTOW) / 30) * headwind_component
            else:
                WIND_FACTOR = ((CALM_MTOW - np.interp(CALM_MTOW, self.CALM_FLAPS5, self.TAILWIND_5_FLAPS5)) / 5) * headwind_component

        MTOW = CALM_MTOW + WIND_FACTOR if wind_type == 'Headwind' else CALM_MTOW - WIND_FACTOR
        return min(MTOW, 25000)

    def crew_onboard_spinner(self, spinner, text):
        print("Selected option:", text)

    def calc_free_button(self):
        pass

class MyApp(App):
    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect('apt.db')
        self.cursor = self.conn.cursor()

    def build(self):
        return MyBoxLayout(cursor=self.cursor)

if __name__ == '__main__':
    MyApp().run()
