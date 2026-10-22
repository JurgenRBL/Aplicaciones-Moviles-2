"""Mascotas Perdidas: reportes locales de animales y su última ubicación."""
import asyncio
from pathlib import Path
import uuid
import time
from datetime import datetime

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

BLUE = "#146B66"
RED = "#DB654D"
NOTICE = "Tus reportes se guardan en este teléfono. No se publican ni se envían a refugios automáticamente."


class App:
    def __init__(self, page, storage):
        self.page, self.storage = page, storage
        self.coordinates = None
        self.user_location = None
        self.evidence = {}
        self.recording = None
        self.camera_ready = False
        self.camera_busy = False
        self.camera_lock = asyncio.Lock()
        self.camera_signal = asyncio.Event()
        self.camera_error = None
        self.media_busy = False
        self.media_hint = "Preparando captura…"
        self.record_started = 0
        self.record_epoch = 0
        self.focus_location = None
        self.camera_supported = getattr(page, "web", False) or getattr(page, "platform", None) in (
            ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        self.geo = fg.Geolocator()
        self.permissions = fp.PermissionHandler()
        self.recorder = fr.AudioRecorder()
        self.player = fa.Audio()
        self.launcher = ft.UrlLauncher()
        page.services.extend([self.geo, self.permissions, self.recorder, self.player, self.launcher])
        self.category = ft.Dropdown(label="¿Qué quieres reportar?", value="Mascota perdida", options=[ft.DropdownOption(x) for x in CATEGORIES])
        self.pet_name = ft.TextField(label="Nombre de la mascota (si lo conoces)", max_length=100)
        self.species = ft.Dropdown(label="Tipo de animal", value="Perro", options=[ft.DropdownOption(x) for x in ("Perro", "Gato", "Ave", "Otro")])
        self.landmark = ft.TextField(label="Barrio o lugar de referencia", hint_text="Ej.: plaza principal, frente a la farmacia", max_length=200)
        self.description = ft.TextField(label="¿Cómo es y dónde la viste?", multiline=True, min_lines=3, max_length=2000)
        self.priority = ft.Dropdown(label="Urgencia", value="Media", options=[ft.DropdownOption(x) for x in PRIORITIES])
        self.coords = ft.Text("Marca el lugar donde viste o perdiste a la mascota.")
        self.status = ft.Text(color=BLUE)
        self.location_preview = ft.Container()
        self.record_text = ft.Text("Listo para grabar", color="white", weight=ft.FontWeight.BOLD, size=18, expand=True)
        self.record_indicator = ft.Container(content=ft.Row([fl.Lottie(src="grabando.json", width=52, height=52, animate=True), self.record_text]), bgcolor=RED, padding=12, border_radius=18, visible=False, animate=ft.Animation(250))
        self.photo_button = self.button("Tomar foto", self.photo, ft.Icons.PHOTO_CAMERA)
        self.video_button = self.button("Grabar video", self.video, ft.Icons.VIDEOCAM)
        self.audio_button = self.button("Grabar nota de voz", self.audio, ft.Icons.MIC)
        self.camera_button = self.button("Abrir cámara", self.open_camera, ft.Icons.CAMERA_ALT)
        self.save_button = self.button("Guardar reporte", self.save, ft.Icons.PETS)
        self.camera_status = ft.Text("La cámara se abrirá al tomar una foto o grabar un video.", color=BLUE)
        self.camera = fc.Camera(height=240, preview_enabled=True, on_state_change=self.on_camera_state)
        self.attachments = ft.Column()
        self.markers = fm.MarkerLayer(markers=[])
        self.map_status = ft.Text("El mapa requiere Internet. Toca un punto para reportar allí.")
        self.map = fm.Map(initial_center=fm.MapLatitudeLongitude(-16.5, -68.15), initial_zoom=13,
            expand=True, on_tap=self.map_tap,
            layers=[fm.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                user_agent_package_name="bo.edu.udabol.alertasegura/1.0 (MascotasPerdidas/1.1 local pet reports)",
                on_image_error=self.tile_error), self.markers])
        # Flet 0.86.5 AnimatedSwitcher builds its child with a new UniqueKey on
        # updates. That disposes the native camera during state/button updates.
        # Keep the screen mounted under a stable container instead.
        self.switcher = ft.Container(content=ft.Container(), expand=True)
        self.body = ft.Container(content=self.switcher, expand=True, padding=16)
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

    def card(self, controls, color="white"):
        return ft.Container(content=ft.Column(controls, spacing=12), bgcolor=color,
            border_radius=22, padding=20)

    def home(self):
        return self.column([
            self.card([
                ft.Row([ft.Image(src="perrito.png", width=72, height=72),
                    ft.Column([ft.Text("Cada huellita", size=21, color="white"),
                        ft.Text("merece volver a casa", size=21, weight=ft.FontWeight.BOLD, color="white")], expand=True)]),
                ft.Text("Reporta una mascota perdida, encontrada o vista cerca de ti.", color="white"),
            ], BLUE),
            fl.Lottie(src="huellitas.json", height=115, animate=True),
            ft.Text("Ayudemos a que se reencuentren", size=23, weight=ft.FontWeight.BOLD, color=BLUE),
            self.button("Reportar una mascota", lambda e: self.show(2), ft.Icons.PETS),
            self.button("Ver mascotas en el mapa", lambda e: self.show(1), ft.Icons.MAP_OUTLINED),
            self.button("Mis reportes guardados", lambda e: self.show(3), ft.Icons.FAVORITE_OUTLINE),
            self.card([ft.Text(f"{len(self.storage.all())} reportes en tu teléfono", size=19, weight=ft.FontWeight.BOLD),
                ft.Text("1. Describe la mascota  ·  2. Marca el lugar  ·  3. Añade fotos o una nota de voz")], "#FFF0D5"),
            ft.Text(NOTICE, size=12, color=BLUE)])

    def point_preview(self, coordinates):
        hint = ft.Text("Último lugar marcado. Puedes acercar el mapa para reconocer las calles.", size=12, color=BLUE)
        def unavailable(e):
            hint.value = "No se pudo cargar el mapa. Comprueba Internet o pulsa Abrir en Google Maps."
            self.page.update()
        minimap = fm.Map(height=200, initial_center=fm.MapLatitudeLongitude(*coordinates), initial_zoom=16,
            layers=[fm.TileLayer(url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                user_agent_package_name="bo.edu.udabol.alertasegura/MascotasPerdidas-1.1",
                on_image_error=unavailable),
                fm.MarkerLayer(markers=[fm.Marker(coordinates=fm.MapLatitudeLongitude(*coordinates),
                    content=ft.Icon(ft.Icons.PETS, color=RED, size=38))])])
        return ft.Column([minimap, hint, ft.TextButton("© OpenStreetMap contributors",
            url="https://www.openstreetmap.org/copyright")], tight=True, spacing=0)

    @staticmethod
    def display_date(value):
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y · %H:%M")
        except (ValueError, TypeError):
            return value

    def refresh_location_preview(self):
        self.location_preview.content = self.point_preview(self.coordinates) if self.coordinates else ft.Text(
            "Aún no marcaste el lugar. Usa mi ubicación si estás allí, o elígelo en el mapa.", color=BLUE)

    def update_recording_ui(self):
        active = self.recording
        self.video_button.content = "Detener video" if active == "video" else "Grabar video"
        self.audio_button.content = "Detener nota de voz" if active == "audio" else "Grabar nota de voz"
        self.video_button.icon = ft.Icons.STOP_CIRCLE if active == "video" else ft.Icons.VIDEOCAM
        self.audio_button.icon = ft.Icons.STOP_CIRCLE if active == "audio" else ft.Icons.MIC
        self.video_button.disabled = self.media_busy or self.camera_busy or active == "audio"
        self.audio_button.disabled = self.media_busy or self.camera_busy or active == "video"
        self.photo_button.disabled = bool(active) or self.media_busy or self.camera_busy
        self.camera_button.disabled = bool(active) or self.media_busy or self.camera_busy or self.camera_ready
        self.camera_button.content = "Preparando cámara…" if self.camera_busy else ("Cámara lista" if self.camera_ready else "Abrir cámara")
        self.save_button.disabled = bool(active) or self.media_busy or self.camera_busy
        self.record_indicator.visible = bool(active) or self.media_busy
        if self.media_busy:
            self.record_text.value = self.media_hint
        elif active:
            elapsed = max(0, int(time.monotonic() - self.record_started))
            self.record_text.value = f"● Grabando {'video' if active == 'video' else 'audio'}  {elapsed // 60:02d}:{elapsed % 60:02d}"
        self.page.update()

    def begin_recording(self, kind):
        self.recording = kind
        self.record_started = time.monotonic()
        self.record_epoch += 1
        if hasattr(self.page, "run_task"):
            self.page.run_task(self.record_clock, self.record_epoch)

    async def record_clock(self, epoch):
        while self.recording and epoch == self.record_epoch:
            self.update_recording_ui()
            await asyncio.sleep(1)

    async def open_external_map(self, coordinates):
        try:
            await self.launcher.launch_url(f"https://www.google.com/maps/search/?api=1&query={coordinates[0]},{coordinates[1]}")
        except Exception as ex:
            self.message(f"No se pudo abrir el mapa del teléfono: {ex}")

    async def view_report_map(self, item):
        await self.close_detail(None)
        self.focus_location = (item["latitude"], item["longitude"])
        self.map_status.value = item.get("landmark") or "Último lugar registrado de esta mascota."
        self.show(1)
        try:
            await self.map.move_to(destination=fm.MapLatitudeLongitude(*self.focus_location), zoom=16)
        except Exception:
            self.message("El lugar está marcado. Espera a que cargue el mapa o abre Google Maps.")

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
        self.refresh_location_preview()
        return self.column([ft.Text("Cuéntanos de esa mascota", size=25, color=BLUE, weight=ft.FontWeight.BOLD),
            ft.Text("Una foto y un lugar claro pueden marcar la diferencia."),
            self.card([self.category, self.pet_name, self.species, self.description, self.priority]),
            self.card([ft.Text("¿Dónde fue vista por última vez?", size=19, weight=ft.FontWeight.BOLD, color=BLUE),
                self.landmark, self.coords, self.location_preview,
                ft.Row([self.button("Usar mi ubicación", self.locate, ft.Icons.MY_LOCATION),
                    self.button("Elegir lugar", lambda e: self.show(1), ft.Icons.MAP)], wrap=True)]),
            self.card([ft.Text("Fotos y recuerdos que ayudan", size=19, weight=ft.FontWeight.BOLD, color=BLUE),
                ft.Text("Puedes añadir una foto, un video breve y una nota de voz."), self.camera_button, self.camera_status,
                self.camera if self.camera_supported else ft.Text("La cámara está disponible al instalar el APK en Android."),
                self.record_indicator,
                ft.Row([self.photo_button, self.video_button, self.audio_button], wrap=True),
                ft.Text("Durante la grabación verás un contador. Pulsa Detener para adjuntar el archivo.", size=12),
                self.attachments, self.status]), self.save_button, ft.Text(NOTICE, size=12, color=BLUE)])

    def navigate(self, e):
        self.show(e.control.selected_index)

    def show(self, index):
        if self.recording or self.media_busy or self.camera_busy:
            self.nav.selected_index = 2
            self.message("Detén la grabación antes de cambiar de sección.")
            return
        self.nav.selected_index = index
        if index == 0:
            content = self.home()
        elif index == 1:
            self.refresh_markers()
            center = self.focus_location or self.user_location or (self.coordinates if self.coordinates else None)
            if center:
                self.map.initial_center = fm.MapLatitudeLongitude(*center)
                self.map.initial_zoom = 16
            content = ft.Column([ft.Text("Lugares donde fueron vistas", size=26), self.map_status,
                ft.Row([self.button("Mi ubicación", self.locate), self.button("Centrar en mí", self.recenter)], wrap=True),
                self.map, ft.Text("© OpenStreetMap contributors · https://www.openstreetmap.org/copyright", size=11)], expand=True)
        elif index == 2:
            content = self.form()
            # Unmounting the camera releases the native controller.
            self.camera_ready = False
            self.camera_signal.clear()
            self.camera_status.value = "La cámara se abrirá al tomar una foto o grabar un video."
        else:
            records = self.storage.all()
            content = self.column([ft.Text("Mis reportes", size=26), ft.Text(NOTICE, color=RED)] + [
                ft.Card(content=ft.ListTile(leading=ft.Icon(ft.Icons.PETS, color=BLUE), title=ft.Text(f'{r.get("pet_name") or r["category"]} · {r.get("species") or "Reporte"}'),
                    subtitle=ft.Text(f'{r["description"][:100]}\n{self.display_date(r["created"])}\n{r.get("landmark") or "Lugar marcado: abre el reporte para verlo en el mapa"}\n' +
                        " · ".join(label for key, label in [("photo", "Foto"), ("video", "Video"), ("audio", "Audio")] if r[key])),
                    on_click=lambda e, item=r: self.detail(item))) for r in records] +
                ([] if records else [fl.Lottie(src="huellitas.json", height=140, animate=True), ft.Text("Aún no hay reportes. Cada búsqueda comienza con una huellita.")]))
        self.switcher.content = content
        self.update_recording_ui()
        self.page.update()

    def map_tap(self, e):
        self.coordinates = (e.coordinates.latitude, e.coordinates.longitude)
        self.focus_location = self.coordinates
        self.coords.value = "Lugar seleccionado. El marcador muestra dónde fue vista la mascota."
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
            self.focus_location = self.coordinates
            self.coords.value = "Ubicación de este teléfono marcada en el mapa."
            self.refresh_location_preview()
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
            self.message("Obtén primero tu ubicación con Mi ubicación.")
            return
        try:
            await self.map.move_to(destination=fm.MapLatitudeLongitude(*self.user_location), zoom=16)
        except Exception as ex:
            self.message(f"No se pudo centrar el mapa: {ex}")

    def on_camera_state(self, event):
        self.camera_error = getattr(event, "error_description", None) if getattr(event, "has_error", False) else None
        self.camera_ready = bool(event.is_initialized) and not self.camera_error
        if self.camera_ready or self.camera_error:
            self.camera_signal.set()
        if self.camera_error:
            self.camera_status.value = f"La cámara necesita volver a abrirse: {self.camera_error}"
        elif self.camera_ready:
            self.camera_status.value = "Cámara lista. Ya puedes tomar fotos o grabar video."
        self.update_recording_ui()

    async def ensure_camera(self):
        async with self.camera_lock:
            if self.camera_ready:
                return
            if not self.camera_supported:
                raise ValueError("La extensión de cámara no admite Windows. Usa el APK en Android.")
            self.camera_busy = True
            self.camera_status.value = "Preparando cámara… espera a que aparezca la imagen."
            self.update_recording_ui()
            try:
                status = await self.permissions.request(fp.Permission.CAMERA)
                if status != fp.PermissionStatus.GRANTED:
                    raise ValueError("Permiso de cámara denegado. Actívalo en Ajustes → Aplicaciones → Mascotas Perdidas → Permisos.")
                cameras = await self.camera.get_available_cameras()
                if not cameras:
                    raise ValueError("No hay cámaras disponibles en este dispositivo.")
                selected = next((c for c in cameras if c.lens_direction == fc.CameraLensDirection.BACK), cameras[0])
                self.camera_signal.clear()
                self.camera_error = None
                await asyncio.wait_for(self.camera.initialize(description=selected,
                    resolution_preset=fc.ResolutionPreset.MEDIUM, enable_audio=False), timeout=25)
                await asyncio.wait_for(self.camera_signal.wait(), timeout=8)
                if not self.camera_ready:
                    raise ValueError(self.camera_error or "No se confirmó la inicialización de la cámara.")
            except Exception as ex:
                self.camera_ready = False
                self.camera_signal.clear()
                self.camera_status.value = f"No se pudo abrir la cámara: {ex or 'se agotó el tiempo de espera'}. Vuelve a pulsar Tomar foto o Grabar video."
                raise
            finally:
                self.camera_busy = False
                self.update_recording_ui()

    async def open_camera(self, e):
        if self.media_busy or self.recording or self.camera_busy:
            return
        try:
            await self.ensure_camera()
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
        if self.media_busy or self.recording or self.camera_busy:
            return
        self.media_busy = True
        self.media_hint = "Preparando fotografía…"
        self.update_recording_ui()
        try:
            await self.ensure_camera()
            self.media_hint = "Tomando fotografía…"
            self.update_recording_ui()
            self.captured(await self.camera.take_picture(), "photo", ".jpg")
            self.message("Fotografía adjuntada.")
        except Exception as ex:
            self.camera_ready = False
            self.message(f"No se pudo tomar la foto: {ex}")
        finally:
            self.media_busy = False
            self.update_recording_ui()

    async def video(self, e):
        if self.media_busy:
            return
        self.media_busy = True
        self.media_hint = "Guardando video…" if self.recording == "video" else "Preparando video…"
        self.update_recording_ui()
        try:
            if self.recording == "video":
                data = await self.camera.stop_video_recording()
                self.recording = None
                self.captured(data, "video", ".mp4")
                self.message("Video adjuntado.")
            elif self.recording:
                raise ValueError("Detén primero el audio.")
            else:
                await self.ensure_camera()
                await self.camera.prepare_for_video_recording()
                await self.camera.start_video_recording()
                self.begin_recording("video")
                self.message("Grabando video. Pulsa otra vez para detener.")
        except Exception as ex:
            self.camera_ready = False
            if self.recording == "video":
                self.recording = None
                self.camera_ready = False
            self.message(f"Error de video: {ex}")

        finally:
            self.media_busy = False
            self.update_recording_ui()

    async def audio(self, e):
        if self.media_busy:
            return
        self.media_busy = True
        self.media_hint = "Guardando nota de voz…" if self.recording == "audio" else "Preparando micrófono…"
        self.update_recording_ui()
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
                self.begin_recording("audio")
                self.message("Grabando audio. Pulsa otra vez para detener.")
        except Exception as ex:
            if self.recording == "audio":
                try:
                    await self.recorder.cancel_recording()
                except Exception:
                    pass
                self.recording = None
            self.message(f"Error de audio: {ex}")

        finally:
            self.media_busy = False
            self.update_recording_ui()

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
            if self.recording or self.media_busy:
                raise ValueError("Detén la grabación antes de guardar.")
            self.storage.save(self.category.value, self.description.value or "", self.coordinates, self.priority.value, self.evidence,
                self.pet_name.value or "", self.species.value or "", self.landmark.value or "")
        except Exception as ex:
            self.message(f"No se guardó: {ex}")
            return
        self.description.value = ""
        self.pet_name.value = ""
        self.landmark.value = ""
        self.coordinates = None
        self.coords.value = "Marca el lugar donde viste o perdiste a la mascota."
        self.evidence = {}
        self.attachments.controls = []
        self.status.value = ""
        self.show(3)
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("¡Una huellita más para ayudar!"),
            content=ft.Column([fl.Lottie(src="confirmacion.json", height=130, animate=True), ft.Text(NOTICE)], tight=True),
            actions=[self.button("Aceptar", lambda e: self.page.pop_dialog())]))

    def detail(self, item):
        self.page.show_dialog(ft.AlertDialog(title=ft.Text(item.get("pet_name") or item["category"]),
            content=ft.Container(width=420, content=ft.Column([
                ft.Text(f'{item["category"]} · {item.get("species") or "Animal"} · Urgencia {item["priority"]}'),
                ft.Text(item["description"]), ft.Text(self.display_date(item["created"])),
                ft.Text(item.get("landmark") or "Último lugar registrado", weight=ft.FontWeight.BOLD),
                self.point_preview((item["latitude"], item["longitude"])),
                self.button("Ver ubicación en el mapa", lambda e: self.page.run_task(self.view_report_map, item), ft.Icons.MAP),
                self.button("Abrir en Google Maps", lambda e: self.page.run_task(self.open_external_map, (item["latitude"], item["longitude"])), ft.Icons.DIRECTIONS),
                *self.evidence_controls(item), ft.Text(NOTICE, size=12)], scroll=ft.ScrollMode.AUTO, tight=True)),
            actions=[self.button("Cerrar", self.close_detail)]))

    async def close_detail(self, e):
        try:
            await self.player.pause()
        except Exception:
            pass
        self.page.pop_dialog()


async def main(page: ft.Page):
    page.title = "Mascotas Perdidas"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=BLUE)
    page.bgcolor = "#F8F6EF"
    page.padding = 0
    page.appbar = ft.AppBar(leading=ft.Image(src="perrito.png", width=44, height=44), title=ft.Text("Mascotas Perdidas", color="white"), bgcolor=BLUE)
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
