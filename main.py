import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from plyer import notification

# Класс будильника
class Alarm:
    def __init__(self, time):
        self.time = time

    def __str__(self):
        return self.time.strftime("%H:%M")

# Главный экран
class MainScreen(BoxLayout):
    alarms = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=10, **kwargs)

        self.add_widget(Label(text="Будильники", font_size=24))

        self.alarm_list = BoxLayout(orientation="vertical", spacing=5)
        self.add_widget(self.alarm_list)

        self.time_input = TextInput(hint_text="HH:MM", size_hint=(1, None), height=40)
        self.add_widget(self.time_input)

        add_button = Button(text="Добавить будильник", size_hint=(1, None), height=50)
        add_button.bind(on_release=self.add_alarm)
        self.add_widget(add_button)

        Clock.schedule_interval(self.check_alarms, 1)

    def add_alarm(self, instance):
        try:
            time = datetime.datetime.strptime(self.time_input.text.strip(), "%H:%M").time()
            alarm = Alarm(time)
            self.alarms.append(alarm)
            self.update_alarm_list()
            self.time_input.text = ""
        except ValueError:
            Popup(title="Ошибка", content=Label(text="Неверный формат времени!"), size_hint=(0.7, 0.3)).open()

    def update_alarm_list(self):
        self.alarm_list.clear_widgets()
        for idx, alarm in enumerate(self.alarms):
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40, spacing=10)
            row.add_widget(Label(text=str(alarm), size_hint=(0.7, 1)))
            delete_button = Button(text="Удалить", size_hint=(0.3, 1))
            delete_button.bind(on_release=lambda instance, index=idx: self.delete_alarm(index))
            row.add_widget(delete_button)
            self.alarm_list.add_widget(row)

    def delete_alarm(self, index):
        del self.alarms[index]
        self.update_alarm_list()

    def check_alarms(self, dt):
        now = datetime.datetime.now().time()
        for alarm in self.alarms:
            if alarm.time.hour == now.hour and alarm.time.minute == now.minute:
                notification.notify(title="Будильник", message="Время просыпаться!", timeout=10)
                self.alarms.remove(alarm)
                self.update_alarm_list()
                break

# Приложение
class AlarmClockApp(App):
    def build(self):
        return MainScreen()

if __name__ == "__main__":
    AlarmClockApp().run()
