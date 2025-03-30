import datetime
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from plyer import notification
from parser import fetch_week_parity

from kivymd.app import MDApp
from kivymd.uix.button import MDFloatingActionButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.pickers import MDTimePicker
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.uix.spinner import Spinner, SpinnerOption

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

class SmallSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.height = 30  # меньшая высота
        self.font_size = "16sp"

# Экран со списком будильников с изменённым интерфейсом
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        # Корневой вертикальный layout
        self.root_layout = BoxLayout(orientation='vertical')
        # Верхняя панель с MDToolbar
        self.toolbar = MDTopAppBar(title="Будильники")
        # Добавляем в правый угол иконку с тремя точками (иконка из Material Design)
        self.toolbar.right_action_items = [["dots-vertical", lambda x: self.open_menu(x)]]
        self.root_layout.add_widget(self.toolbar)

        # Основной контент в вертикальном BoxLayout
        self.content_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # MDLabel для отображения текущей недели (чётная/нечётная)
        self.week_label = MDLabel(
            text=f"Сейчас идёт {current_week_type()} неделя",
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_style="H6",
            size_hint_y=None,
            height=40
        )
        self.content_layout.add_widget(self.week_label)

        # Надпись "Добавьте свой первый будильник!" (будет скрываться при наличии хотя бы одного будильника)
        self.empty_label = MDLabel(
            text="Добавьте свой первый будильник!",
            halign="center",
            theme_text_color="Hint",
            size_hint_y=None,
            height=30
        )
        self.content_layout.add_widget(self.empty_label)

        # Контейнер для списка будильников в ScrollView
        self.alarm_list_scroll = ScrollView()
        self.alarm_list_box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.alarm_list_box.bind(minimum_height=self.alarm_list_box.setter("height"))
        self.alarm_list_scroll.add_widget(self.alarm_list_box)
        self.content_layout.add_widget(self.alarm_list_scroll)

        self.root_layout.add_widget(self.content_layout)

        # Нижняя панель с полупрозрачным фоном и круглой кнопкой добавления
        self.bottom_container = MDCard(
            size_hint=(1, None),
            height=80,
            radius=[20, 20, 20, 20],
            md_bg_color=(0.15, 0.15, 0.15, 1),
            padding=10
        )
        bottom_layout = BoxLayout()
        # Кнопка добавления будильника (FAB)
        self.add_button = MDFloatingActionButton(
            icon="plus",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            on_release=self.go_to_add_alarm
        )
        bottom_layout.add_widget(Widget())  # пустой виджет для центрирования
        bottom_layout.add_widget(self.add_button)
        bottom_layout.add_widget(Widget())
        self.bottom_container.add_widget(bottom_layout)
        self.root_layout.add_widget(self.bottom_container)

        self.add_widget(self.root_layout)

        # Инициализация меню для настроек (выпадающее меню)
        self.menu_items = [{
            "viewclass": "OneLineListItem",
            "text": "Настройки",
            "on_release": lambda: self.menu_callback("settings")
        }]
        self.menu = MDDropdownMenu(
            caller=self.toolbar.ids.right_actions,
            items=self.menu_items,
            width_mult=4
        )

    def open_menu(self, instance):
        self.menu.caller = instance
        self.menu.open()

    def menu_callback(self, text_item):
        self.menu.dismiss()
        if text_item == "settings" or text_item == "Настройки":
            MDApp.get_running_app().sm.current = "settings"

    def go_to_add_alarm(self, instance):
        app = MDApp.get_running_app()
        edit_screen = app.sm.get_screen("edit")
        edit_screen.alarm_index = None
        app.sm.current = "edit"

    def update_alarm_list(self):
        self.alarm_list_box.clear_widgets()
        app = MDApp.get_running_app()
        # Обновляем сообщение о неделе
        self.week_label.text = f"Сейчас идёт {app.current_week} неделя"
        if not app.alarms:
            self.empty_label.opacity = 1
        else:
            # Скрываем надпись, если есть хотя бы один будильник
            self.empty_label.opacity = 0
            for idx, alarm in enumerate(app.alarms):
                # Каждый будильник отображается в горизонтальном BoxLayout
                alarm_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
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
        app = MDApp.get_running_app()
        edit_screen = app.sm.get_screen("edit")
        edit_screen.alarm_index = index
        app.sm.current = "edit"

    def delete_alarm(self, index):
        app = MDApp.get_running_app()
        del app.alarms[index]
        self.update_alarm_list()

# Экран для создания и редактирования будильников (без изменений)
class AlarmEditScreen(Screen):
    def __init__(self, **kwargs):
        super(AlarmEditScreen, self).__init__(**kwargs)
        self.alarm_index = None

        # Корневой вертикальный layout
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Верхняя панель: слева - кнопка "назад", справа - чекбокс "Активен"
        top_bar = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50)
        back_button = MDIconButton(icon="arrow-left", on_release=self.cancel)
        top_bar.add_widget(back_button)
        top_bar.add_widget(BoxLayout())  # заполнитель для распределения пространства

        active_layout = BoxLayout(orientation='horizontal', size_hint=(None, 1), width=150, spacing=5)
        active_label = Label(text="Активен", size_hint=(None, 1), width=80, color=(1,1,1,1))
        self.active_checkbox = MDCheckbox(active=True)
        # Задаём светлый цвет для рамок чекбокса
        self.active_checkbox.unchecked_color = (1,1,1,1)
        self.active_checkbox.active_color = (0.4, 0.8, 0.4, 1)
        active_layout.add_widget(active_label)
        active_layout.add_widget(self.active_checkbox)
        top_bar.add_widget(active_layout)
        self.layout.add_widget(top_bar)

        # Секция для выбора дней недели – обёрнута в MDCard и центрирована
        self.days_card = MDCard(
            orientation='vertical',
            padding=10,
            spacing=10,
            radius=[20, 20, 20, 20],
            md_bg_color=(0.2, 0.2, 0.2, 1),
            size_hint=(None, None),
            size=("300dp", "300dp")
        )
        self.day_inputs = {}  # {день: (MDCheckbox, Button)}
        for day in DAYS_OF_WEEK:
            row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
            checkbox = MDCheckbox(active=False)
            checkbox.unchecked_color = (1, 1, 1, 1)
            checkbox.active_color = (0.4, 0.8, 0.4, 1)
            day_label = Label(text=day, size_hint=(0.3, 1), color=(1,1,1,1), font_size="18sp")
            time_btn = MDIconButton(icon="clock-outline", text="Выбрать время", size_hint=(0.7, 1))
            # Изначально кнопка недоступна, если чекбокс не активен
            time_btn.disabled = not checkbox.active
            checkbox.bind(active=lambda instance, value, btn=time_btn: setattr(btn, "disabled", not value))
            time_btn.bind(on_release=lambda inst, d=day: self.open_time_picker(d))
            row.add_widget(checkbox)
            row.add_widget(day_label)
            row.add_widget(time_btn)
            self.days_card.add_widget(row)
            self.day_inputs[day] = (checkbox, time_btn)

        # Центрируем карточку с днями недели
        from kivy.uix.anchorlayout import AnchorLayout
        days_container = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))
        days_container.add_widget(self.days_card)
        self.layout.add_widget(days_container)

        # Секция для выбора типа недели
        week_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=40, spacing=10)
        week_label = Label(text="Тип недели:", size_hint=(0.3, 1), color=(1,1,1,1))
        self.week_spinner = Spinner(
            text="любая",
            values=["любая", "чётная", "нечётная"],
            size_hint=(0.7, 1),
            height=30,
            option_cls=SmallSpinnerOption  # используем кастомный класс опций
        )
        week_layout.add_widget(week_label)
        week_layout.add_widget(self.week_spinner)
        self.layout.add_widget(week_layout)

        self.add_widget(self.layout)

        # Нижняя панель: прямоугольник с округлёнными углами и круглой кнопкой с галочкой для сохранения
        self.bottom_card = MDCard(
            size_hint=(1, None),
            height=80,
            radius=[20, 20, 20, 20],
            md_bg_color=(0.15, 0.15, 0.15, 1),
            padding=10
        )
        bottom_layout = BoxLayout()
        self.save_button = MDFloatingActionButton(
            icon="check",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            on_release=self.save_alarm
        )
        bottom_layout.add_widget(BoxLayout())  # заполнитель для центрирования
        bottom_layout.add_widget(self.save_button)
        bottom_layout.add_widget(BoxLayout())
        self.bottom_card.add_widget(bottom_layout)
        self.layout.add_widget(self.bottom_card)

    def open_time_picker(self, day):
        time_picker = MDTimePicker()
        checkbox, time_btn = self.day_inputs[day]
        try:
            current_time = datetime.datetime.strptime(time_btn.text, "%H:%M").time()
            time_picker.set_time(current_time)
        except Exception:
            pass
        time_picker.bind(time=lambda instance, t, d=day: self.on_time_selected(d, t))
        time_picker.open()

    def on_time_selected(self, day, time_value):
        checkbox, time_btn = self.day_inputs[day]
        time_btn.text = time_value.strftime("%H:%M")

    def on_pre_enter(self, *args):
        # Если редактируется существующий будильник, заполняем поля данными
        if self.alarm_index is not None:
            alarm = MDApp.get_running_app().alarms[self.alarm_index]
            for day, (checkbox, time_btn) in self.day_inputs.items():
                if day in alarm.schedule:
                    checkbox.active = True
                    time_btn.text = alarm.schedule[day].strftime("%H:%M")
                else:
                    checkbox.active = False
                    time_btn.text = "Выбрать время"
            self.week_spinner.text = alarm.week_type
            self.active_checkbox.active = alarm.active
        else:
            # Для нового будильника очищаем все поля
            for day, (checkbox, time_btn) in self.day_inputs.items():
                checkbox.active = False
                time_btn.text = "Выбрать время"
            self.week_spinner.text = "любая"
            self.active_checkbox.active = True

    def save_alarm(self, instance):
        schedule = {}
        for day, (checkbox, time_btn) in self.day_inputs.items():
            if checkbox.active:
                time_str = time_btn.text.strip()
                if time_str == "Выбрать время":
                    popup = Popup(title="Ошибка",
                                  content=Label(text=f"Для дня {day} выберите время!"),
                                  size_hint=(0.8, 0.3))
                    popup.open()
                    return
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
        # Сохраняем новый или изменённый будильник
        if self.alarm_index is not None:
            MDApp.get_running_app().alarms[self.alarm_index] = type(MDApp.get_running_app().alarms[self.alarm_index])(
                schedule=schedule, week_type=week_type, active=active)
        else:
            from __main__ import Alarm  # предполагаем, что класс Alarm импортирован из главного модуля
            MDApp.get_running_app().alarms.append(Alarm(schedule=schedule, week_type=week_type, active=active))
        MDApp.get_running_app().update_alarm_list()
        MDApp.get_running_app().sm.current = "main"

    def cancel(self, instance):
        MDApp.get_running_app().sm.current = "main"

# Экран настроек (без изменений)
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        title = Label(text="Настройки", font_size=24, size_hint=(1, None), height=40)
        self.layout.add_widget(title)
        self.layout.add_widget(Label(text="Длительность отложения (мин):"))
        from kivy.uix.textinput import TextInput
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
        app = MDApp.get_running_app()
        self.snooze_input.text = str(app.snooze_duration)
        self.notifications_checkbox.active = app.enable_notifications

    def save_settings(self, instance):
        app = MDApp.get_running_app()
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
        MDApp.get_running_app().sm.current = "main"

# Главное приложение
class AlarmClockApp(MDApp):
    alarms = ListProperty([])
    snooze_duration = NumericProperty(5)
    enable_notifications = BooleanProperty(True)

    def build(self):
        self.title = "Продвинутый будильник"

        # Тёмная тема
        self.theme_cls.theme_style = "Dark"
        # Основной цвет (можно менять)
        self.theme_cls.primary_palette = "DeepPurple"
        self.sm = ScreenManager()
        self.main_screen = MainScreen(name="main")
        self.sm.add_widget(self.main_screen)
        self.edit_screen = AlarmEditScreen(name="edit")
        self.sm.add_widget(self.edit_screen)
        self.settings_screen = SettingsScreen(name="settings")
        self.sm.add_widget(self.settings_screen)
        self.current_week = "любая"
        self.update_current_week(0)
        Clock.schedule_interval(self.check_alarms, 1)
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
                            break  # Прерываем цикл, чтобы не срабатывать повторно в ту же секунду

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
        # Обновляем информацию в week_label, если экран уже создан
        if hasattr(self, "main_screen"):
            self.main_screen.week_label.text = f"Сейчас идёт {self.current_week} неделя"

if __name__ == '__main__':
    AlarmClockApp().run()
