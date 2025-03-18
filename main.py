import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from plyer import notification

# Импорт функции синхронизации недели из parser.py
from parser import fetch_week_parity

# Список дней недели (на русском)
DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# Класс будильника
class Alarm:
    def __init__(self, schedule=None, week_type="любая", active=True):
        """
        :param schedule: словарь, где ключ – день недели (str), а значение – объект datetime.time
        :param week_type: "любая", "чётная" или "нечётная"
        :param active: активен ли будильник
        """
        self.schedule = schedule if schedule is not None else {}
        self.week_type = week_type
        self.active = active
        self.last_triggered = None  # время последнего срабатывания

    def __str__(self):
        if not self.schedule:
            schedule_str = "Нет дней"
        else:
            schedule_str = ", ".join([f"{day}: {time.strftime('%H:%M')}" for day, time in self.schedule.items()])
        return f"{schedule_str} (Неделя: {self.week_type})"

# Определение чётности недели по системной дате (для справки)
def is_even_week():
    week_number = datetime.date.today().isocalendar()[1]
    return week_number % 2 == 0

def current_week_type():
    return "чётная" if is_even_week() else "нечётная"

# Экран со списком будильников
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        title_label = Label(text="Список будильников", font_size=24, size_hint=(1, None), height=40)
        self.layout.add_widget(title_label)

        self.alarm_list_box = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, 0.7))
        self.layout.add_widget(self.alarm_list_box)

        button_panel = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, 0.15))
        add_button = Button(text="Добавить будильник")
        add_button.bind(on_release=self.go_to_add_alarm)
        settings_button = Button(text="Настройки")
        settings_button.bind(on_release=self.go_to_settings)
        button_panel.add_widget(add_button)
        button_panel.add_widget(settings_button)
        self.layout.add_widget(button_panel)

        self.add_widget(self.layout)

    def go_to_add_alarm(self, instance):
        app = App.get_running_app()
        edit_screen = app.sm.get_screen("edit")
        edit_screen.alarm_index = None
        app.sm.current = "edit"

    def go_to_settings(self, instance):
        App.get_running_app().sm.current = "settings"

    def update_alarm_list(self):
        self.alarm_list_box.clear_widgets()
        app = App.get_running_app()
        if not app.alarms:
            self.alarm_list_box.add_widget(Label(text="Нет установленных будильников"))
        else:
            for idx, alarm in enumerate(app.alarms):
                alarm_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
                alarm_label = Label(text=str(alarm), size_hint=(0.6, 1))
                edit_button = Button(text="Редактировать", size_hint=(0.2, 1))
                edit_button.bind(on_release=lambda instance, index=idx: self.edit_alarm(index))
                delete_button = Button(text="Удалить", size_hint=(0.2, 1))
                delete_button.bind(on_release=lambda instance, index=idx: self.delete_alarm(index))
                alarm_layout.add_widget(alarm_label)
                alarm_layout.add_widget(edit_button)
                alarm_layout.add_widget(delete_button)
                self.alarm_list_box.add_widget(alarm_layout)

    def edit_alarm(self, index):
        app = App.get_running_app()
        edit_screen = app.sm.get_screen("edit")
        edit_screen.alarm_index = index
        app.sm.current = "edit"

    def delete_alarm(self, index):
        app = App.get_running_app()
        del app.alarms[index]
        self.update_alarm_list()

# Экран для создания и редактирования будильников
class AlarmEditScreen(Screen):
    def __init__(self, **kwargs):
        super(AlarmEditScreen, self).__init__(**kwargs)
        self.alarm_index = None
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.layout.add_widget(Label(text="Настройка будильника", font_size=20, size_hint=(1, None), height=40))
        self.layout.add_widget(Label(text="Выберите дни и укажите время (HH:MM):"))
        
        # Создаем поля для каждого дня недели
        self.day_inputs = {}  # формат: {день: (CheckBox, TextInput)}
        for day in DAYS_OF_WEEK:
            row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
            checkbox = CheckBox(active=False, size_hint=(0.1, 1))
            label = Label(text=day, size_hint=(0.3, 1))
            time_input = TextInput(hint_text="HH:MM", multiline=False, size_hint=(0.6, 1))
            time_input.disabled = not checkbox.active
            checkbox.bind(active=lambda instance, value, inp=time_input: setattr(inp, "disabled", not value))
            row.add_widget(checkbox)
            row.add_widget(label)
            row.add_widget(time_input)
            self.layout.add_widget(row)
            self.day_inputs[day] = (checkbox, time_input)
        
        # Выбор типа недели
        self.layout.add_widget(Label(text="Тип недели:"))
        self.week_spinner = Spinner(
            text="любая",
            values=["любая", "чётная", "нечётная"],
            size_hint=(1, None),
            height=40
        )
        self.layout.add_widget(self.week_spinner)
        
        # Чекбокс для активности будильника
        checkbox_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40)
        self.active_checkbox = CheckBox(active=True)
        checkbox_layout.add_widget(Label(text="Активен", size_hint=(0.8, 1)))
        checkbox_layout.add_widget(self.active_checkbox)
        self.layout.add_widget(checkbox_layout)
        
        # Кнопки "Сохранить" и "Отмена"
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=40)
        save_button = Button(text="Сохранить")
        save_button.bind(on_release=self.save_alarm)
        cancel_button = Button(text="Отмена")
        cancel_button.bind(on_release=self.cancel)
        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)
        self.layout.add_widget(button_layout)
        
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        if self.alarm_index is not None:
            alarm = App.get_running_app().alarms[self.alarm_index]
            for day, (checkbox, time_input) in self.day_inputs.items():
                if day in alarm.schedule:
                    checkbox.active = True
                    time_input.text = alarm.schedule[day].strftime("%H:%M")
                else:
                    checkbox.active = False
                    time_input.text = ""
            self.week_spinner.text = alarm.week_type
            self.active_checkbox.active = alarm.active
        else:
            for day, (checkbox, time_input) in self.day_inputs.items():
                checkbox.active = False
                time_input.text = ""
            self.week_spinner.text = "любая"
            self.active_checkbox.active = True

    def save_alarm(self, instance):
        schedule = {}
        for day, (checkbox, time_input) in self.day_inputs.items():
            if checkbox.active:
                time_str = time_input.text.strip()
                try:
                    day_time = datetime.datetime.strptime(time_str, "%H:%M").time()
                    schedule[day] = day_time
                except ValueError:
                    popup = Popup(title="Ошибка",
                                  content=Label(text=f"Неверный формат времени для {day}. Используйте HH:MM"),
                                  size_hint=(0.8, 0.3))
                    popup.open()
                    return
        week_type = self.week_spinner.text
        active = self.active_checkbox.active
        new_alarm = Alarm(schedule=schedule, week_type=week_type, active=active)
        app = App.get_running_app()
        if self.alarm_index is not None:
            app.alarms[self.alarm_index] = new_alarm
        else:
            app.alarms.append(new_alarm)
        app.update_alarm_list()
        app.sm.current = "main"

    def cancel(self, instance):
        App.get_running_app().sm.current = "main"

# Экран настроек (без изменений)
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        title = Label(text="Настройки", font_size=24, size_hint=(1, None), height=40)
        self.layout.add_widget(title)
        self.layout.add_widget(Label(text="Длительность отложения (мин):"))
        self.snooze_input = TextInput(text="5", multiline=False, size_hint=(1, None), height=40)
        self.layout.add_widget(self.snooze_input)
        checkbox_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40)
        self.notifications_checkbox = CheckBox(active=True)
        checkbox_layout.add_widget(Label(text="Включить уведомления", size_hint=(0.8, 1)))
        checkbox_layout.add_widget(self.notifications_checkbox)
        self.layout.add_widget(checkbox_layout)
        button_layout = BoxLayout(orientation="horizontal", spacing=10, size_hint=(1, None), height=40)
        save_button = Button(text="Сохранить")
        save_button.bind(on_release=self.save_settings)
        cancel_button = Button(text="Отмена")
        cancel_button.bind(on_release=self.cancel)
        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)
        self.layout.add_widget(button_layout)
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.snooze_input.text = str(app.snooze_duration)
        self.notifications_checkbox.active = app.enable_notifications

    def save_settings(self, instance):
        app = App.get_running_app()
        try:
            app.snooze_duration = int(self.snooze_input.text)
        except ValueError:
            popup = Popup(title="Ошибка",
                          content=Label(text="Неверное значение длительности"),
                          size_hint=(0.8, 0.3))
            popup.open()
            return
        app.enable_notifications = self.notifications_checkbox.active
        app.sm.current = "main"

    def cancel(self, instance):
        App.get_running_app().sm.current = "main"

# Главное приложение
class AlarmClockApp(App):
    alarms = ListProperty([])
    snooze_duration = NumericProperty(5)
    enable_notifications = BooleanProperty(True)

    def build(self):
        self.title = "Продвинутый будильник"
        self.sm = ScreenManager()
        self.main_screen = MainScreen(name="main")
        self.sm.add_widget(self.main_screen)
        self.edit_screen = AlarmEditScreen(name="edit")
        self.sm.add_widget(self.edit_screen)
        self.settings_screen = SettingsScreen(name="settings")
        self.sm.add_widget(self.settings_screen)
        # Изначально текущая неделя по синхронизации
        self.current_week = "любая"
        # Немедленно обновляем актуальную чётность недели
        self.update_current_week(0)
        # Запускаем проверку будильников каждую секунду
        Clock.schedule_interval(self.check_alarms, 1)
        # Обновляем актуальную неделю раз в час
        Clock.schedule_interval(self.update_current_week, 3600)
        return self.sm

    def update_alarm_list(self):
        self.main_screen.update_alarm_list()

    def check_alarms(self, dt):
        now = datetime.datetime.now()
        today = datetime.date.today()
        current_day = DAYS_OF_WEEK[today.weekday()]  # Текущий день недели
        for alarm in self.alarms:
            if alarm.active and current_day in alarm.schedule:
                scheduled_time = alarm.schedule[current_day]
                alarm_dt = datetime.datetime.combine(today, scheduled_time)
                # Если время срабатывания в пределах 1 секунды и прошло >60 сек с последнего срабатывания
                if abs((alarm_dt - now).total_seconds()) < 1:
                    if alarm.last_triggered is None or (now - alarm.last_triggered).total_seconds() > 60:
                        # Срабатываем, только если тип будильника "любая" или совпадает с актуальной неделей
                        if alarm.week_type == "любая" or alarm.week_type == self.current_week:
                            print("Будильник сработал!")
                            if self.enable_notifications:
                                try:
                                    notification.notify(title="Будильник", message="Время просыпаться!", timeout=10)
                                except NotImplementedError:
                                    print("Уведомления не поддерживаются на этой платформе.")
                            alarm.last_triggered = now
                            self.show_alarm_popup(alarm)
                            break  # прерываем цикл, чтобы не срабатывать повторно в ту же секунду

    def show_alarm_popup(self, alarm):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Будильник сработал!"))
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=40)
        snooze_button = Button(text="Отложить")
        dismiss_button = Button(text="Отключить")
        button_layout.add_widget(snooze_button)
        button_layout.add_widget(dismiss_button)
        content.add_widget(button_layout)
        popup = Popup(title="Будильник", content=content, size_hint=(0.8, 0.4))
        
        def snooze(instance):
            now_dt = datetime.datetime.now()
            new_dt = now_dt + datetime.timedelta(minutes=self.snooze_duration)
            today_name = DAYS_OF_WEEK[datetime.date.today().weekday()]
            if today_name in alarm.schedule:
                alarm.schedule[today_name] = new_dt.time()
            popup.dismiss()
            self.update_alarm_list()
        
        def dismiss(instance):
            alarm.active = False
            popup.dismiss()
            self.update_alarm_list()

        snooze_button.bind(on_release=snooze)
        dismiss_button.bind(on_release=dismiss)
        popup.open()

    def update_current_week(self, dt):
        week_parity = fetch_week_parity()
        if week_parity is not None:
            if week_parity == "even":
                self.current_week = "чётная"
            elif week_parity == "odd":
                self.current_week = "нечётная"
            else:
                self.current_week = "любая"
        else:
            self.current_week = "любая"

if __name__ == '__main__':
    AlarmClockApp().run()
