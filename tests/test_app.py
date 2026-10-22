import sys
import tempfile
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from storage import Storage
from main import App
import flet_geolocator as fg


class FakePage:
    def __init__(self):
        self.services = []
        self.dialogs = []

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)


class AppTests(unittest.TestCase):
    def test_save_reopen_and_media(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Storage(root / "app")
            source = root / "foto.jpg"
            source.write_bytes(b"test photo")
            photo = store.attach(source, "photo")
            identifier = store.save("Robo", "Prueba de persistencia", (-16.5, -68.15), "Alta", {"photo": photo})
            source.unlink()
            reopened = Storage(root / "app").all()
            self.assertEqual(len(reopened), 1)
            self.assertEqual(reopened[0]["id"], identifier)
            self.assertEqual(reopened[0]["latitude"], -16.5)
            self.assertEqual(Path(reopened[0]["photo"]).read_bytes(), b"test photo")

    def test_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Storage(directory)
            for category, description, coords, priority in [
                ("Robo", "", (-16, -68), "Alta"),
                ("Robo", "Prueba", None, "Alta"),
                ("Robo", "Prueba", (91, 0), "Alta"),
                ("Robo", "Prueba", (float("nan"), 0), "Alta"),
                ("Inválida", "Prueba", (0, 0), "Alta")]:
                with self.assertRaises(ValueError):
                    store.save(category, description, coords, priority, {})
            self.assertEqual(store.all(), [])

    def test_navigation_save_history_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            page = FakePage()
            app = App(page, Storage(directory))
            for index in range(4):
                app.show(index)
                self.assertEqual(app.nav.selected_index, index)
                self.assertIsNotNone(app.body.content)
            app.description.value = "Incidente de prueba"
            app.coordinates = (-16.5, -68.15)
            app.save(None)
            self.assertEqual(len(app.storage.all()), 1)
            self.assertEqual(app.nav.selected_index, 3)
            app.show(1)
            self.assertEqual(len(app.markers.markers), 1)
            app.recording = "video"
            app.show(0)
            self.assertEqual(app.nav.selected_index, 2)


class ServiceFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_gps_disabled_denied_and_success(self):
        with tempfile.TemporaryDirectory() as directory:
            app = App(FakePage(), Storage(directory))
            app.geo = SimpleNamespace(is_location_service_enabled=AsyncMock(return_value=False))
            await app.locate(None)
            self.assertIsNone(app.coordinates)
            self.assertIn("Activa el GPS", app.status.value)
            app.geo = SimpleNamespace(is_location_service_enabled=AsyncMock(return_value=True),
                request_permission=AsyncMock(return_value=fg.GeolocatorPermissionStatus.DENIED))
            await app.locate(None)
            self.assertIsNone(app.coordinates)
            self.assertIn("denegado", app.status.value)
            app.geo.request_permission.return_value = fg.GeolocatorPermissionStatus.WHILE_IN_USE
            app.geo.get_current_position = AsyncMock(return_value=SimpleNamespace(latitude=-16.5, longitude=-68.15))
            await app.locate(None)
            self.assertEqual(app.coordinates, (-16.5, -68.15))
            self.assertEqual(app.user_location, app.coordinates)

    async def test_photo_video_and_audio_file_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            app = App(FakePage(), Storage(directory))
            app.camera = SimpleNamespace(take_picture=AsyncMock(return_value=b"image bytes"),
                start_video_recording=AsyncMock(), stop_video_recording=AsyncMock(return_value=b"video bytes"))
            app.camera_ready = True
            await app.photo(None)
            self.assertEqual(Path(app.evidence["photo"]).read_bytes(), b"image bytes")
            await app.video(None)
            self.assertEqual(app.recording, "video")
            await app.video(None)
            self.assertIsNone(app.recording)
            self.assertEqual(Path(app.evidence["video"]).read_bytes(), b"video bytes")
            temporary = Path(directory) / "grabacion-temporal.wav"
            app.recorder = SimpleNamespace(has_permission=AsyncMock(return_value=True),
                start_recording=AsyncMock(return_value=True), stop_recording=AsyncMock(return_value=str(temporary)))
            await app.audio(None)
            self.assertEqual(app.recording, "audio")
            temporary.write_bytes(b"audio bytes")
            await app.audio(None)
            self.assertIsNone(app.recording)
            self.assertEqual(Path(app.evidence["audio"]).read_bytes(), b"audio bytes")


if __name__ == "__main__":
    unittest.main()
