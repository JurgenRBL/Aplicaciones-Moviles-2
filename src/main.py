"""Alerta Segura: cuatro pantallas y servicios nativos Flet."""
import asyncio
from pathlib import Path
import uuid

import flet as ft
import flet_camera as fc
import flet_map as fm
import flet_geolocator as fg
import flet_lottie as fl
import flet_audio as fa
import flet_audio_recorder as fr
import flet_video as fv
import flet_permission_handler as fp
from storage import Storage, CATEGORIES, PRIORITIES

BLUE = "#122B49"
RED = "#D9364F"
NOTICE = "Registros locales. No constituyen una denuncia oficial ni se envían a la Policía."


class App:
    def __init__(self, page, storage):
        self.page, self.storage = page, storage
        self.coordinates = None
        self.user_location = None
        self.evidence = {}
        self.recording = None
        self.camera_ready = False
        self.camera_supported = getattr(page, "web", False) or getattr(page, "platform", None) in (
            ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        self.geo = fg.Geolocator()
        self.permissions = fp.PermissionHandler()
        self.recorder = fr.AudioRecorder()
        self.player = fa.Audio()
        page.services.extend([self.geo, self.permissions, self.recorder, self.player])
        self.category = ft.Dropdown(label="Categoría", value="Robo", options=[ft.DropdownOption(x) for x in CATEGORIES])
        self.description = ft.TextField(label="¿Qué ocurrió?", multiline=True, min_lines=3, max_length=2000)
        self.priority = ft.Dropdown(label="Prioridad", value="Media", options=[ft.DropdownOption(x) for x in PRIORITIES])
        self.coords = ft.Text("Sin ubicación. Usa GPS o selecciona un punto del mapa.")
        self.status = ft.Text(color=RED)
        self.camera = fc.Camera(height=240, preview_enabled=True)
        self.attachments = ft.Column()
        self.markers = fm.MarkerLayer(markers=[])
        self.map_status = ft.Text("El mapa requiere Internet. Toca un punto para reportar allí.")
        self.map = fm.Map(initial_center=fm.MapLatitudeLongitude(-16.5, -68.15), initial_zoom=13,
            expand=True, on_tap=self.map_tap,
            layers=[fm.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                user_agent_package_name="bo.edu.udabol.alertasegura/1.0 (academic local incident app)",
                on_image_error=self.tile_error), self.markers])
        self.body = ft.Container(expand=True, padding=16)
        self.nav = ft.NavigationBar(selected_index=0, on_change=self.navigate,
            destinations=[ft.NavigationBarDestination(icon=icon, label=label) for icon, label in [
                (ft.Icons.HOME_OUTLINED, "Inicio"), (ft.Icons.MAP_OUTLINED, "Mapa"),
                (ft.Icons.ADD_LOCATION_ALT_OUTLINED, "Reportar"), (ft.Icons.HISTORY, "Historial")]])

    def message(self, value):
        self.status.value = value
        self.page.show_dialog(ft.SnackBar(ft.Text(value)))
        self.page.update()

    def tile_error(self, e):
        self.map_status.value = "No se pudieron cargar las teselas. Comprueba Internet y vuelve a abrir Mapa."
        self.page.update()

    def column(self, controls):
        return ft.Column(controls, scroll=ft.ScrollMode.AUTO, expand=True, spacing=16)

    def button(self, label, handler, icon=None):
        return ft.Button(label, on_click=handler, icon=icon)

    def home(self):
        return self.column([
            ft.Container(content=ft.Column([
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=64, color="white"),
                ft.Text("Alerta Segura", size=30, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Documenta un incidente con ubicación y evidencias.", color="white"),
            ]), bgcolor=BLUE, border_radius=20, padding=24),
            fl.Lottie(src="confirmacion.json", height=120, animate=True),
            ft.Text("Tu registro, en un solo lugar", size=22, weight=ft.FontWeight.BOLD),
            self.button("Registrar un incidente", lambda e: self.show(2), ft.Icons.ADD_LOCATION_ALT),
            self.button("Explorar el mapa", lambda e: self.show(1), ft.Icons.MAP),
            self.button("Consultar historial", lambda e: self.show(3), ft.Icons.HISTORY),
            ft.Text(f"{len(self.storage.all())} incidentes guardados en este dispositivo."),
            ft.Text(NOTICE, color=RED), ft.Text("UDABOL · Aplicaciones Móviles II", size=12)])

    def refresh_markers(self):
        markers = []
        if self.user_location:
            markers.append(fm.Marker(coordinates=fm.MapLatitudeLongitude(*self.user_location),
                content=ft.Icon(ft.Icons.MY_LOCATION, color=BLUE, size=30)))
        for incident in self.storage.all():
            markers.append(fm.Marker(coordinates=fm.MapLatitudeLongitude(incident["latitude"], incident["longitude"]),
                content=ft.IconButton(icon=ft.Icons.LOCATION_ON, icon_color=RED, tooltip=incident["category"],
                    on_click=lambda e, item=incident: self.detail(item))))
        self.markers.markers = markers

    def form(self):
        return self.column([ft.Text("Nuevo incidente", size=26, weight=ft.FontWeight.BOLD),
            ft.Text("La fecha y hora se asignan al guardar."), self.category, self.description, self.priority,
            self.coords, ft.Row([self.button("Obtener GPS", self.locate), self.button("Elegir en mapa", lambda e: self.show(1))], wrap=True),
            ft.Text("Evidencias opcionales", size=20, weight=ft.FontWeight.BOLD),
            self.button("Activar cámara", self.open_camera, ft.Icons.CAMERA_ALT),
            self.camera if self.camera_supported else ft.Text("La cámara requiere Android, iOS o web. En Windows puedes probar formulario, audio, mapa e historial."),
            ft.Row([self.button("Tomar fotografía", self.photo), self.button("Grabar / detener video", self.video),
                self.button("Grabar / detener audio", self.audio)], wrap=True),
            ft.Text("Detén la grabación antes de guardar o cambiar de pantalla."), self.attachments, self.status,
            self.button("Guardar incidente", self.save, ft.Icons.SAVE), ft.Text(NOTICE, color=RED)])

    def navigate(self, e):
        self.show(e.control.selected_index)

    def show(self, index):
        if self.recording:
            self.nav.selected_index = 2
            self.message("Detén la grabación antes de cambiar de sección.")
            return
        self.nav.selected_index = index
        if index == 0:
            content = self.home()
        elif index == 1:
            self.refresh_markers()
            content = ft.Column([ft.Text("Mapa de incidentes", size=26), self.map_status,
                ft.Row([self.button("Actualizar GPS", self.locate), self.button("Centrar en mí", self.recenter)], wrap=True),
                self.map, ft.Text("© OpenStreetMap contributors · https://www.openstreetmap.org/copyright", size=11)], expand=True)
        elif index == 2:
            content = self.form()
            # Unmounting the camera releases the native controller.
            self.camera_ready = False
        else:
            records = self.storage.all()
            content = self.column([ft.Text("Historial local", size=26), ft.Text(NOTICE, color=RED)] + [
                ft.Card(content=ft.ListTile(title=ft.Text(f'{r["category"]} · {r["priority"]}'),
                    subtitle=ft.Text(f'{r["description"][:100]}\n{r["created"]}\n{r["latitude"]:.5f}, {r["longitude"]:.5f}\n' +
                        " · ".join(label for key, label in [("photo", "Foto"), ("video", "Video"), ("audio", "Audio")] if r[key])),
                    on_click=lambda e, item=r: self.detail(item))) for r in records] +
                ([] if records else [ft.Text("Todavía no hay incidentes. Registra el primero en Reportar.")]))
        self.body.content = content
        self.page.update()

    def map_tap(self, e):
        self.coordinates = (e.coordinates.latitude, e.coordinates.longitude)
        self.coords.value = f"Punto elegido: {self.coordinates[0]:.6f}, {self.coordinates[1]:.6f}"
        self.show(2)

    async def locate(self, e):
        try:
            if not await self.geo.is_location_service_enabled():
                raise ValueError("Activa el GPS en los ajustes del dispositivo.")
            permission = await self.geo.request_permission()
            if permission not in (fg.GeolocatorPermissionStatus.WHILE_IN_USE, fg.GeolocatorPermissionStatus.ALWAYS):
                raise ValueError("Permiso de ubicación denegado. Puedes habilitarlo en Ajustes de la aplicación.")
            position = await asyncio.wait_for(self.geo.get_current_position(), timeout=30)
            self.user_location = self.coordinates = (position.latitude, position.longitude)
            self.coords.value = f"GPS: {position.latitude:.6f}, {position.longitude:.6f}"
            self.map_status.value = self.coords.value
            self.refresh_markers()
            self.page.update()
            if self.nav.selected_index == 1:
                await self.recenter(None)
            self.message("Ubicación actualizada.")
        except Exception as ex:
            self.message(f"No se obtuvo la ubicación: {ex or 'tiempo de espera agotado'}")

    async def recenter(self, e):
        if self.user_location is None:
            self.message("Obtén primero tu ubicación con Actualizar GPS.")
            return
        try:
            await self.map.move_to(destination=fm.MapLatitudeLongitude(*self.user_location), zoom=16)
        except Exception as ex:
            self.message(f"No se pudo centrar el mapa: {ex}")

    async def open_camera(self, e):
        try:
            if not self.camera_supported:
                raise ValueError("La extensión de cámara no admite Windows. Usa el APK en Android.")
            if self.recording:
                raise ValueError("Detén primero la grabación.")
            status = await self.permissions.request(fp.Permission.CAMERA)
            if status != fp.PermissionStatus.GRANTED:
                raise ValueError("Permiso de cámara denegado. Revísalo en Ajustes.")
            cameras = await self.camera.get_available_cameras()
            if not cameras:
                raise ValueError("No hay cámaras disponibles en este dispositivo.")
            # Video sin sonido: la nota de voz se captura de forma independiente.
            await self.camera.initialize(cameras[0], fc.ResolutionPreset.MEDIUM, enable_audio=False)
            self.camera_ready = True
            self.message("Cámara lista. El video se graba sin sonido; puedes añadir una nota de voz.")
        except Exception as ex:
            self.camera_ready = False
            self.message(f"No se pudo activar la cámara: {ex}")

    def captured(self, data, kind, suffix):
        if not data:
            raise ValueError("La captura está vacía.")
        target = self.storage.media / (uuid.uuid4().hex + suffix)
        target.write_bytes(data)
        self.evidence[kind] = str(target)
        self.render_evidence()

    async def photo(self, e):
        try:
            if not self.camera_ready or self.recording:
                raise ValueError("Activa la cámara y detén cualquier grabación.")
            self.captured(await self.camera.take_picture(), "photo", ".jpg")
            self.message("Fotografía adjuntada.")
        except Exception as ex:
            self.message(f"No se pudo tomar la foto: {ex}")

    async def video(self, e):
        try:
            if self.recording == "video":
                data = await self.camera.stop_video_recording()
                self.recording = None
                self.captured(data, "video", ".mp4")
                self.message("Video adjuntado.")
            elif self.recording:
                raise ValueError("Detén primero el audio.")
            elif not self.camera_ready:
                raise ValueError("Activa primero la cámara.")
            else:
                await self.camera.start_video_recording()
                self.recording = "video"
                self.message("Grabando video. Pulsa otra vez para detener.")
        except Exception as ex:
            self.message(f"Error de video: {ex}")

    async def audio(self, e):
        try:
            if self.recording == "audio":
                path = await self.recorder.stop_recording()
                self.recording = None
                if not path:
                    raise ValueError("No se generó el archivo de audio.")
                self.evidence["audio"] = self.storage.attach(path, "audio")
                Path(path).unlink(missing_ok=True)
                self.render_evidence()
                self.message("Nota de voz adjuntada.")
            elif self.recording:
                raise ValueError("Detén primero el video.")
            else:
                if not await self.recorder.has_permission():
                    raise ValueError("Permiso de micrófono denegado. Revísalo en Ajustes.")
                path = str(self.storage.root / "grabacion-temporal.wav")
                if not await self.recorder.start_recording(output_path=path):
                    raise ValueError("El micrófono no pudo iniciar.")
                self.recording = "audio"
                self.message("Grabando audio. Pulsa otra vez para detener.")
        except Exception as ex:
            self.message(f"Error de audio: {ex}")

    async def play_audio(self, path):
        try:
            await self.player.pause()
            self.player.src = path
            self.page.update()
            await self.player.play()
        except Exception as ex:
            self.message(f"No se pudo reproducir el audio: {ex}")

    def evidence_controls(self, evidence):
        controls = []
        if evidence.get("photo"):
            controls.append(ft.Image(src=evidence["photo"], height=180, fit=ft.BoxFit.CONTAIN))
        if evidence.get("video"):
            controls.append(fv.Video(playlist=[fv.VideoMedia(evidence["video"])], height=220, autoplay=False, show_controls=True))
        if evidence.get("audio"):
            async def play(e):
                await self.play_audio(evidence["audio"])
            controls.extend([self.button("Reproducir nota de voz", play, ft.Icons.PLAY_ARROW),
                self.button("Pausar audio", lambda e: self.page.run_task(self.player.pause))])
        return controls

    def render_evidence(self):
        self.attachments.controls = self.evidence_controls(dict(self.evidence))
        self.page.update()

    def save(self, e):
        try:
            if self.recording:
                raise ValueError("Detén la grabación antes de guardar.")
            self.storage.save(self.category.value, self.description.value or "", self.coordinates, self.priority.value, self.evidence)
        except Exception as ex:
            self.message(f"No se guardó: {ex}")
            return
        self.description.value = ""
        self.coordinates = None
        self.coords.value = "Sin ubicación. Usa GPS o selecciona un punto del mapa."
        self.evidence = {}
        self.attachments.controls = []
        self.status.value = ""
        self.show(3)
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Incidente guardado"),
            content=ft.Column([fl.Lottie(src="confirmacion.json", height=130, animate=True), ft.Text(NOTICE)], tight=True),
            actions=[self.button("Aceptar", lambda e: self.page.pop_dialog())]))

    def detail(self, item):
        self.page.show_dialog(ft.AlertDialog(title=ft.Text(f'{item["category"]} · Prioridad {item["priority"]}'),
            content=ft.Container(width=420, content=ft.Column([
                ft.Text(item["description"]), ft.Text(item["created"]),
                ft.Text(f'{item["latitude"]:.6f}, {item["longitude"]:.6f}'),
                *self.evidence_controls(item), ft.Text(NOTICE, size=12)], scroll=ft.ScrollMode.AUTO, tight=True)),
            actions=[self.button("Cerrar", self.close_detail)]))

    async def close_detail(self, e):
        await self.player.pause()
        self.page.pop_dialog()


async def main(page: ft.Page):
    page.title = "Alerta Segura"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=BLUE)
    page.bgcolor = "#F3F6FA"
    page.padding = 0
    page.appbar = ft.AppBar(title=ft.Text("Alerta Segura", color="white"), bgcolor=BLUE)
    paths = ft.StoragePaths()
    page.services.append(paths)
    try:
        root = Path(await paths.get_application_support_directory()) / "AlertaSegura"
        app = App(page, Storage(root))
        page.add(app.body)
        page.navigation_bar = app.nav
        app.show(0)
    except Exception as ex:
        page.add(ft.Text(f"No se pudo iniciar el almacenamiento local: {ex}"))


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
