import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from plyer import notification

SNOOZE_DURATION = 5  # длительность отложения в минутах

# Класс будильника с возможностью активации/деактивации
class Alarm:
    def __init__(self, time, active=True):
        self.time = time
        self.active = active

    def __str__(self):
        status = "Активен" if self.active else "Отключен"
        return f"{self.time.strftime('%H:%M')} ({status})"

# Главный экран с функционалом добавления, редактирования, удаления и проверки будильников
class MainScreen(BoxLayout):
    alarms = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=10, **kwargs)
        self.add_widget(Label(text="Будильники", font_size=24))

        # Список для отображения будильников
        self.alarm_list = BoxLayout(orientation="vertical", spacing=5)
        self.add_widget(self.alarm_list)

        # Поле ввода для добавления нового будильника
        self.time_input = TextInput(hint_text="HH:MM", size_hint=(1, None), height=40)
        self.add_widget(self.time_input)

        add_button = Button(text="Добавить будильник", size_hint=(1, None), height=50)
        add_button.bind(on_release=self.add_alarm)
        self.add_widget(add_button)

        # Проверка срабатывания будильников каждую секунду
        Clock.schedule_interval(self.check_alarms, 1)

    def add_alarm(self, instance):
        try:
            time = datetime.datetime.strptime(self.time_input.text.strip(), "%H:%M").time()
            alarm = Alarm(time)
            self.alarms.append(alarm)
            self.update_alarm_list()
            self.time_input.text = ""
        except ValueError:
            Popup(title="Ошибка", 
                  content=Label(text="Неверный формат времени!"),
                  size_hint=(0.7, 0.3)).open()

    def update_alarm_list(self):
        self.alarm_list.clear_widgets()
        for idx, alarm in enumerate(self.alarms):
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40, spacing=10)
            row.add_widget(Label(text=str(alarm), size_hint=(0.5, 1)))
            # Кнопка редактирования будильника
            edit_button = Button(text="Редактировать", size_hint=(0.25, 1))
            edit_button.bind(on_release=lambda instance, index=idx: self.open_edit_popup(index))
            row.add_widget(edit_button)
            # Кнопка удаления будильника
            delete_button = Button(text="Удалить", size_hint=(0.25, 1))
            delete_button.bind(on_release=lambda instance, index=idx: self.delete_alarm(index))
            row.add_widget(delete_button)
            self.alarm_list.add_widget(row)

    def delete_alarm(self, index):
        del self.alarms[index]
        self.update_alarm_list()

    def open_edit_popup(self, index):
        alarm = self.alarms[index]
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text="Редактировать будильник"))

        # Поле ввода времени с текущим значением
        time_input = TextInput(text=alarm.time.strftime("%H:%M"), multiline=False, size_hint=(1, None), height=40)
        content.add_widget(time_input)

        # Переключатель для активации/деактивации
        active_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=40)
        active_layout.add_widget(Label(text="Активен", size_hint=(0.7, 1)))
        active_checkbox = CheckBox(active=alarm.active)
        active_layout.add_widget(active_checkbox)
        content.add_widget(active_layout)

        # Кнопки сохранения и отмены
        button_layout = BoxLayout(orientation="horizontal", spacing=10, size_hint=(1, None), height=40)
        save_button = Button(text="Сохранить")
        cancel_button = Button(text="Отмена")
        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)
        content.add_widget(button_layout)

        popup = Popup(title="Редактирование", content=content, size_hint=(0.8, 0.5))

        def save(instance):
            try:
                new_time = datetime.datetime.strptime(time_input.text.strip(), "%H:%M").time()
                alarm.time = new_time
                alarm.active = active_checkbox.active
                self.update_alarm_list()
                popup.dismiss()
            except ValueError:
                Popup(title="Ошибка", 
                      content=Label(text="Неверный формат времени!"),
                      size_hint=(0.7, 0.3)).open()

        save_button.bind(on_release=save)
        cancel_button.bind(on_release=lambda instance: popup.dismiss())
        popup.open()

    def check_alarms(self, dt):
        now = datetime.datetime.now().time()
        for alarm in self.alarms:
            if alarm.active and alarm.time.hour == now.hour and alarm.time.minute == now.minute:
                self.show_alarm_popup(alarm)
                break

    def show_alarm_popup(self, alarm):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text="Будильник сработал!"))
        button_layout = BoxLayout(orientation="horizontal", spacing=10, size_hint=(1, None), height=40)
        snooze_button = Button(text="Отложить")
        dismiss_button = Button(text="Отключить")
        button_layout.add_widget(snooze_button)
        button_layout.add_widget(dismiss_button)
        content.add_widget(button_layout)

        popup = Popup(title="Будильник", content=content, size_hint=(0.8, 0.4))

        def snooze(instance):
            # При отложении устанавливаем новое время через SNOOZE_DURATION минут
            now_dt = datetime.datetime.now()
            new_dt = now_dt + datetime.timedelta(minutes=SNOOZE_DURATION)
            alarm.time = new_dt.time()
            self.update_alarm_list()
            popup.dismiss()

        def dismiss(instance):
            alarm.active = False
            self.update_alarm_list()
            popup.dismiss()

        snooze_button.bind(on_release=snooze)
        dismiss_button.bind(on_release=dismiss)
        popup.open()

# Приложение
class AlarmClockApp(App):
    def build(self):
        return MainScreen()

if __name__ == "__main__":
    AlarmClockApp().run()
