# Copyright (c) 2025, Tomasz Pakuła Using Arch BTW

from gi.repository import Gtk, Adw, GLib

from .button_row import FoxblatButtonRow
from .switch_row import FoxblatSwitchRow
from .advance_row import FoxblatAdvanceRow
from .label_row import FoxblatLabelRow

from foxblat.subscription import EventDispatcher
from foxblat import process_handler
from foxblat import steam_handler
from foxblat.preset_handler import MozaPresetHandler
from os import environ, path

def _process_display_name(cmdline: str) -> str:
    """Return just the executable filename from a full command line pattern."""
    if not cmdline:
        return ""
    exe = cmdline.split()[0].replace("\\", "/")
    return path.basename(exe) or cmdline


# Combo row indices
_LINK_MODE_STEAM = 0
_LINK_MODE_PROCESS = 1


class FoxblatPresetDialog(Adw.Dialog, EventDispatcher):
    def __init__(self, presets_path: str, file_name: str, simapi_handler=None):
        Adw.Dialog.__init__(self)
        EventDispatcher.__init__(self)

        self._process_list_group = None
        self._simapi = simapi_handler
        self._current_vehicle_from_simapi = ""
        self._preset_handler = MozaPresetHandler(None)
        self._preset_handler.set_path(presets_path)
        self._preset_handler.set_name(file_name)

        self._register_events("save",  "delete")

        self._initial_name = file_name.removesuffix(".yml")
        preset_name = file_name.removesuffix(".yml")
        self._preset_name = preset_name
        self.set_title("Preset settings")
        self.set_content_width(480)

        # Stored link values
        self._process_pattern = self._preset_handler.get_linked_process()
        self._steam_appid = self._preset_handler.get_linked_steam_appid()
        self._steam_name = self._preset_handler.get_linked_steam_name()

        # has_link reflects only what was explicitly saved — must be read before auto-select
        has_link = bool(self._process_pattern or self._steam_appid)

        # Determine initial link mode from saved data.
        # Default to Steam unless there is an explicit process link (and no Steam link).
        initial_mode = _LINK_MODE_PROCESS if (self._process_pattern and not self._steam_appid) else _LINK_MODE_STEAM

        # --- Name row ---
        self._name_row = Adw.EntryRow(title="Preset name")
        self._name_row.set_text(preset_name)

        # --- Auto apply toggle ---
        self._auto_apply = FoxblatSwitchRow("Apply automatically")
        self._auto_apply.set_subtitle("Apply when the selected game or process is running")

        # --- Link mode selector (Steam game vs custom process) ---
        self._link_mode_combo = Adw.ComboRow()
        self._link_mode_combo.set_title("Link type")
        link_model = Gtk.StringList.new(["Steam game", "Custom process"])
        self._link_mode_combo.set_model(link_model)
        self._link_mode_combo.set_selected(initial_mode)
        self._link_mode_combo.set_sensitive(False)
        self._auto_apply.subscribe(self._link_mode_combo.set_sensitive)

        # --- Steam game section ---
        steam_display = self._steam_name if self._steam_name else "No Steam game linked"
        self._steam_name_row = FoxblatLabelRow("Game")
        self._steam_name_row.set_wrap(True)
        self._steam_name_row.set_label(steam_display)

        self._steam_select_row = FoxblatAdvanceRow("Select running Steam game")
        self._steam_select_row.subscribe(self._open_steam_page)

        # --- Process section ---
        self._auto_apply_name = FoxblatLabelRow("Process")
        self._auto_apply_name.set_wrap(True)
        self._auto_apply_name.set_label(_process_display_name(self._process_pattern))

        self._auto_apply_select = FoxblatAdvanceRow("Select running process")
        self._auto_apply_select.subscribe(self._open_process_page)

        # Connect link mode changes to show/hide Steam vs process rows
        self._link_mode_combo.connect("notify::selected", self._on_link_mode_changed)
        self._auto_apply.subscribe(self._on_auto_apply_changed)

        # Apply initial visibility — hide both sections when auto-apply is off
        self._update_link_mode_visibility(initial_mode if has_link else -1)
        self._auto_apply.set_value(has_link, mute=False)

        # --- Vehicle linking ---
        linked_vehicle = self._preset_handler.get_linked_vehicle()
        self._link_vehicle = FoxblatSwitchRow("Link to current vehicle")
        self._link_vehicle.set_subtitle("Apply only when driving this car")
        self._link_vehicle.set_active(False)
        self._auto_apply.subscribe(self._link_vehicle.set_active)

        self._vehicle_name_row = FoxblatLabelRow("Vehicle")
        self._vehicle_name_row.set_wrap(True)
        self._vehicle_name_row.set_label(linked_vehicle if linked_vehicle else "No vehicle detected")
        self._vehicle_name_row.set_active(False)
        self._link_vehicle.subscribe(self._vehicle_name_row.set_active)

        self._link_vehicle.set_value(len(linked_vehicle) > 0, mute=False)

        if simapi_handler:
            simapi_handler.subscribe("car-name", self._on_vehicle_update)
            current_car = simapi_handler.get_current_car_name()
            if current_car:
                self._on_vehicle_update(current_car)

        # --- Default preset toggle ---
        self._default = FoxblatSwitchRow("Default preset", "Activate if no other automatic preset applies")
        self._default.set_value(self._preset_handler.is_default())

        # --- Build page layout ---
        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup(margin_start=10, margin_end=10)
        group.add(self._name_row)
        page.add(group)

        group = Adw.PreferencesGroup(margin_start=10, margin_end=10)
        group.add(self._auto_apply)
        group.add(self._link_mode_combo)
        group.add(self._steam_name_row)
        group.add(self._steam_select_row)
        group.add(self._auto_apply_name)
        group.add(self._auto_apply_select)
        group.add(self._link_vehicle)
        group.add(self._vehicle_name_row)
        page.add(group)

        group = Adw.PreferencesGroup(margin_start=10, margin_end=10)
        group.add(self._default)
        page.add(group)

        nav = Adw.NavigationView()
        self.set_child(nav)
        self._navigation = nav

        toolbar_view = Adw.ToolbarView()
        nav.add(Adw.NavigationPage(title="Preset settings", child=toolbar_view))
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(page)

        self._save_row = None
        self._delete_row = None

        if Adw.get_minor_version() >= 6:
            self._save_row = Adw.ButtonRow(title="Save")
            self._save_row.add_css_class("suggested-action")
            self._save_row.set_end_icon_name("document-save-symbolic")
            self._save_row.connect("activated", self._notify_save)
            self._name_row.connect("notify::text-length", lambda e, *args: self._save_row.set_sensitive(e.get_text_length()))

            self._delete_row = Adw.ButtonRow(title="Delete")
            self._delete_row.add_css_class("destructive-action")
            self._delete_row.set_end_icon_name("user-trash-symbolic")
            self._delete_row.connect("activated", self._notify_delete)

            group = Adw.PreferencesGroup(margin_start=100, margin_end=100)
            group.add(self._delete_row)
            page.add(group)

            group = Adw.PreferencesGroup(margin_start=100, margin_end=100)
            group.add(self._save_row)
            page.add(group)

        else:
            self._save_row = Gtk.Button(label="Save", hexpand=True)
            self._save_row.add_css_class("suggested-action")
            self._save_row.add_css_class("square")
            self._save_row.connect("clicked", self._notify_save)
            self._name_row.connect("notify::text-length", lambda e, *args: self._save_row.set_sensitive(e.get_text_length()))

            self._delete_row = Gtk.Button(label="Delete", hexpand=True)
            self._delete_row.add_css_class("destructive-action")
            self._delete_row.add_css_class("square")
            self._delete_row.connect("clicked", self._notify_delete)

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.append(self._delete_row)
            box.append(self._save_row)
            box.add_css_class("linked")
            self.get_child().add_bottom_bar(box)


    def _on_auto_apply_changed(self, value) -> None:
        active = bool(value)
        mode = self._link_mode_combo.get_selected()
        self._update_link_mode_visibility(mode if active else -1)
        if active and mode == _LINK_MODE_STEAM:
            self._try_auto_select_steam()


    def _on_link_mode_changed(self, combo, *args) -> None:
        if not self._auto_apply.get_value():
            return
        self._update_link_mode_visibility(combo.get_selected())
        if combo.get_selected() == _LINK_MODE_STEAM:
            self._try_auto_select_steam()


    def _try_auto_select_steam(self) -> None:
        """Auto-select the only running Steam game if none is linked yet."""
        if self._steam_appid:
            return
        running = steam_handler.detect_running_steam_games()
        if len(running) == 1:
            self._steam_appid = running[0].app_id
            self._steam_name = running[0].name
            self._steam_name_row.set_label(running[0].name)


    def _update_link_mode_visibility(self, mode: int) -> None:
        steam_visible = mode == _LINK_MODE_STEAM
        process_visible = mode == _LINK_MODE_PROCESS

        self._steam_name_row.set_visible(steam_visible)
        self._steam_select_row.set_visible(steam_visible)
        self._auto_apply_name.set_visible(process_visible)
        self._auto_apply_select.set_visible(process_visible)


    def _on_vehicle_update(self, vehicle_name: str):
        self._current_vehicle_from_simapi = vehicle_name
        if vehicle_name:
            GLib.idle_add(self._vehicle_name_row.set_label, vehicle_name)


    def _notify_save(self, *rest):
        self.close()

        mode = self._link_mode_combo.get_selected()

        if self._auto_apply.get_value() and mode == _LINK_MODE_STEAM:
            # Save Steam link, clear process link
            self._preset_handler.set_linked_steam_appid(self._steam_appid)
            self._preset_handler.set_linked_steam_name(self._steam_name)
            self._preset_handler.set_linked_process("")
        elif self._auto_apply.get_value() and mode == _LINK_MODE_PROCESS:
            # Save process link, clear Steam link
            self._preset_handler.set_linked_process(self._process_pattern)
            self._preset_handler.set_linked_steam_appid("")
            self._preset_handler.set_linked_steam_name("")
        else:
            # Auto-apply disabled — clear everything
            self._preset_handler.set_linked_process("")
            self._preset_handler.set_linked_steam_appid("")
            self._preset_handler.set_linked_steam_name("")

        # Save vehicle link if enabled and we have a vehicle
        vehicle_name = ""
        if self._auto_apply.get_value() and self._link_vehicle.get_value():
            if self._current_vehicle_from_simapi:
                vehicle_name = self._current_vehicle_from_simapi
            else:
                vehicle_name = self._preset_handler.get_linked_vehicle()
        self._preset_handler.set_linked_vehicle(vehicle_name)

        self._preset_handler.set_default(self._default.get_value())

        current_name = self._name_row.get_text()
        if self._initial_name != current_name:
            self._preset_handler.copy_preset(current_name)
            self._dispatch("delete", self._preset_name)

        self._dispatch("save", self._preset_name)


    def _notify_delete(self, *rest):
        self.close()
        self._dispatch("delete", self._preset_name)


    # ------------------------------------------------------------------ Steam game page

    def _open_steam_page(self, *rest):
        running = steam_handler.detect_running_steam_games()

        # Auto-select when exactly one game is running — no need to show the picker
        if len(running) == 1:
            self._select_steam_game(running[0], navigate_back=False)
            return

        group = Adw.PreferencesGroup()

        if not running:
            group.add(FoxblatLabelRow("No Steam games detected"))
        else:
            for game in running:
                row = Adw.ActionRow()
                row.set_title(game.name)
                row.set_subtitle(f"AppID: {game.app_id}")
                row.connect("activated", lambda r, g=game: self._select_steam_game(g))
                row.set_activatable(True)
                group.add(row)

        page = Adw.PreferencesPage()
        page.add(group)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(page)

        self._navigation.push(Adw.NavigationPage(title="Select Steam game", child=toolbar_view))


    def _select_steam_game(self, game: steam_handler.SteamGame, navigate_back: bool = True):
        if navigate_back:
            self._navigation.pop()
        self._steam_appid = game.app_id
        self._steam_name = game.name
        self._steam_name_row.set_label(game.name)


    # ------------------------------------------------------------------ Process page

    def _list_processes(self, entry: Adw.EntryRow, page: Adw.PreferencesPage):
        group = Adw.PreferencesGroup()
        filter_text = entry.get_text()

        if len(filter_text) < 3:
            group.add(FoxblatLabelRow("Enter at least three letters"))
        else:
            processes = process_handler.list_processes(filter_text)

            if not processes:
                group.add(FoxblatLabelRow("No matching processes found"))
            else:
                processes.sort(key=lambda p: p.name.lower())

                for process_info in processes:
                    row = Adw.ActionRow()
                    row.set_title(process_info.name)

                    if process_info.cmdline != process_info.name:
                        cmdline_display = process_info.cmdline
                        if len(cmdline_display) > 80:
                            cmdline_display = cmdline_display[:77] + "..."
                        row.set_subtitle(cmdline_display)

                    row.connect("activated", lambda r, cmd=process_info.cmdline: self._select_process(cmd))
                    row.set_activatable(True)
                    group.add(row)

        old_group = self._process_list_group
        self._process_list_group = group

        def swap_groups():
            page.remove(old_group)
            page.add(group)

        GLib.idle_add(swap_groups)


    def _select_process(self, cmdline_pattern: str):
        self._navigation.pop()
        self._process_pattern = cmdline_pattern
        self._auto_apply_name.set_label(_process_display_name(cmdline_pattern))


    def _open_process_page(self, *rest):
        entry = Adw.EntryRow()
        entry.set_title("Process name filter")

        group = Adw.PreferencesGroup()
        group.add(entry)
        self._process_list_group = Adw.PreferencesGroup(title="Process list")

        page = Adw.PreferencesPage()
        page.add(group)
        page.add(self._process_list_group)

        entry.connect("notify::text-length", lambda *_: self._list_processes(entry, page))

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(page)

        self._navigation.push(Adw.NavigationPage(title="Find game process", child=toolbar_view))
        self._list_processes(entry, page)
