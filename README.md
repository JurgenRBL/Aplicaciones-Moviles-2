# Alerta Segura

Proyecto académico de Aplicaciones Móviles II, UDABOL. Registra incidentes **solo en el dispositivo**: no envía denuncias oficiales ni mensajes externos.

## Tecnología y referencia

Python + Flet 0.86.5, siguiendo las prácticas del [repositorio de la materia](https://github.com/Jack625a/DesarrolloAplicacionesMovilesII-II-2026-UDABOL) revisadas en `app`, `animaciones`, `googemaps` y `sensores` (commit `308c4a5b88876a18b014d4c085ff287fbb30f698`). Cámara integrada con flet-camera; flet-audio-recorder y flet-audio para voz; flet-video para reproducción; flet-geolocator, flet-map y flet-lottie. SQLite de la biblioteca estándar. Las prácticas de referencia se conservaron sin cambios. Proyecto publicado en [JurgenRBL/Aplicaciones-Moviles-2](https://github.com/JurgenRBL/Aplicaciones-Moviles-2).

## Ejecución en Windows

Desde PowerShell, dentro de esta carpeta:

```powershell
# El entorno .venv ya está preparado en esta entrega.
.\.venv\Scripts\python src/main.py
```

Para reconstruir el entorno en otra computadora (Python 3.10 o posterior):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m pip install flet-cli==0.86.5 flet-desktop==0.86.5
.\.venv\Scripts\python src/main.py
```

Para Android, instala Android Studio con SDK y herramientas de línea de comandos, acepta las licencias del SDK y ejecuta:

```powershell
$env:PIP_NO_CACHE_DIR = '1'
.\.venv\Scripts\flet build apk --arch arm64-v8a --yes
```

Flet descarga la versión de Flutter requerida y dependencias nativas; la primera compilación requiere Internet y espacio en disco. Se desactiva la caché pip porque la caché existente en este equipo produjo demoras y errores de deserialización. El APK resultante se coloca en `build/apk`. ARM64 corresponde a teléfonos actuales; para un emulador x86_64 cambia a `--arch x86_64`. Requiere **Android 7 o posterior (API 24)** por las dependencias nativas actuales. El proyecto usa las extensiones nativas: el cliente genérico de pruebas de Flet podría no incluirlas; para la demostración móvil usa el APK compilado. No se requiere servidor.

Se fija [JNI 1.1.0](https://pub.dev/packages/jni/versions/1.1.0) mediante `tool.flet.flutter.pubspec.dependency_overrides`: la plantilla Flet 0.86.5 fuerza 1.0.0, mientras las versiones resueltas de `shared_preferences_android` y `jni_flutter` generan bindings que requieren 1.1. La corrección vive en `pyproject.toml`, por lo que se conserva al regenerar Android.

## Funciones

- Inicio, Mapa, Reportar e Historial mediante navegación inferior.
- Categoría, descripción obligatoria, prioridad, fecha/hora y ubicación obligatoria.
- Cámara integrada: activar, tomar foto y ver la vista previa; iniciar/detener video y reproducirlo. **Video sin sonido**; la nota de voz se graba por separado.
- Iniciar/detener audio, reproducir y pausar la nota de voz.
- GPS a petición, control de servicio desactivado/permisos y espera máxima de 30 segundos.
- Mapa con zoom por gestos, marcadores seleccionables, punto elegido tocando el mapa y botón para volver al usuario.
- SQLite y evidencias en el directorio privado de soporte de la aplicación, obtenido mediante StoragePaths. Las coordenadas del formulario se limpian después de guardar, para evitar reutilizar una ubicación por accidente.
- Lottie local original `src/assets/confirmacion.json`, creado para este proyecto, sin descargas ni licencias de terceros. Se utiliza al inicio y en la confirmación.

## Permisos y mapa

Manifest configurado en `pyproject.toml`: Internet, cámara, micrófono y ubicación aproximada/precisa. Los permisos de cámara, voz y GPS se solicitan al usar cada función. No hay seguimiento en segundo plano. La aplicación utiliza archivos privados y no solicita acceso al almacenamiento compartido; el manifiesto fusionado también hereda declaraciones de lectura/escritura externa de dependencias de Flet, sin que esta aplicación las solicite en tiempo de ejecución. Ante una denegación permanente, habilita el permiso desde Ajustes → Aplicaciones → Alerta Segura.

Se utiliza `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, con identificación de la aplicación y atribución visible. No necesita clave. Requiere Internet; un fallo de teselas muestra un aviso. Cumplir la [política de teselas de OSM](https://operations.osmfoundation.org/policies/tiles/): sin precarga masiva ni descarga para uso offline. El servicio no garantiza disponibilidad. Para uso masivo, contratar un proveedor y cambiar URL/atribución en `src/main.py`.

El endpoint de clase `https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}` coincide técnicamente con la plantilla XYZ, pero no se habilita porque no se confirmó autorización para acceder directamente a ese endpoint. La [API oficial de teselas satelitales](https://developers.google.com/maps/documentation/tile/satellite) requiere clave y sesión, además de sus [políticas de uso](https://developers.google.com/maps/documentation/tile/policies). OSM mantiene el proyecto sencillo y sin claves.

## Verificación y límites

**Entrega verificada el 22/10/2026:** compilación Android finalizada correctamente, APK ARM64 en `build/apk/alerta-segura.apk` (aproximadamente 71 MB). Nombre y paquete comprobados con `aapt`; mínimo API 24, objetivo API 36. Firma APK v2 verificada con `apksigner`. Compilación Python, compatibilidad de dependencias y las cinco pruebas automatizadas completadas correctamente.

Copia `build/apk/alerta-segura.apk` a un teléfono Android 7 o posterior con procesador ARM64, abre el archivo e instala la aplicación. Android puede pedir habilitar la instalación desde esa aplicación de archivos. Después abre **Alerta Segura** y concede cámara, micrófono y ubicación cuando los utilices. No hace falta configurar una clave de mapas.

### Instalación en el celular

Descarga el APK desde [Releases de este proyecto](https://github.com/JurgenRBL/Aplicaciones-Moviles-2/releases/latest) directamente en el teléfono, o utiliza la copia local siguiendo estos pasos:

1. Conecta el teléfono Android a la computadora mediante un cable USB y selecciona **Transferencia de archivos**.
2. Copia `build/apk/alerta-segura.apk` a la carpeta **Descargas** del teléfono.
3. En el teléfono, abre **Archivos → Descargas → alerta-segura.apk** y pulsa **Instalar**. Si Android lo pide, permite instalar desde esa aplicación de archivos.
4. Abre **Alerta Segura**, entra a **Reportar** y concede los permisos al utilizar cámara, audio y GPS. Prueba un incidente y vuelve a abrir la aplicación para comprobar su persistencia.

Para instalar desde una computadora con ADB, habilita **Depuración USB**, conecta y desbloquea el teléfono y acepta la autorización de esa computadora. Ejecuta `adb devices` y luego `adb install -r build/apk/alerta-segura.apk`. La opción `-r` actualiza una instalación compatible conservando sus datos; no es necesario desinstalar antes. Consulta la [documentación oficial de ADB](https://developer.android.com/tools/adb) y las [opciones de distribución de Android](https://developer.android.com/distribute/marketing-tools/alternative-distribution).

El APK es para Android y no puede instalarse en iPhone. La instalación del APK funciona sin GitHub; para distribuirlo desde GitHub se puede adjuntar a una Release, mientras el código fuente se publica sin `.venv`, carpetas de compilación ni registros personales.

**Samsung Galaxy S7 edge:** comprueba la versión en **Ajustes → Acerca del teléfono → Información de software → Versión de Android**. Este APK necesita Android 7 o posterior y ARM64. Samsung publicó Android 8 para variantes del S7 edge, como [SM-G935F](https://doc.samsungmobile.com/SM-G935F/004681190404/eng.html); eso no confirma la versión instalada en tu unidad. Si aún tiene Android 6, este APK no podrá instalarse. En Android 8, al abrir el APK, permite la instalación desde **Mis archivos** o el navegador cuando el sistema lo solicite. En Android 7, el ajuste puede aparecer como **Orígenes desconocidos** dentro de Seguridad. Después de instalar, prueba foto, video breve, voz y GPS antes de la exposición; todavía no se ha validado el hardware de ese teléfono.

```powershell
.\.venv\Scripts\python -m compileall -q src
.\.venv\Scripts\python -m pip check
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Las cinco pruebas automáticas comprueban validación, persistencia tras reabrir SQLite, conservación de evidencias tras borrar el original, construcción y cambio de las cuatro pantallas, guardado desde formulario y actualización de marcadores. También comprueban GPS desactivado, permisos denegados y flujos de captura con servicios simulados. Las pruebas de interfaz usan un Page simulado: no acreditan renderizado ni interacción nativa.

Pendiente validar en Android físico: permisos, cámara, captura y reproducción de video/audio, GPS, interacción con mapa y renderizado Lottie. No se considera probado un sensor solo porque exista su código. `adb devices` no detectó ningún dispositivo conectado. Se inició el cliente Windows y se corrigió el fallo de navegación provocado por montar la cámara en una plataforma incompatible.

Limitaciones deliberadas: una foto, un video y una nota por incidente; nuevas capturas reemplazan la selección del borrador. Al abandonar un borrador, sus archivos pueden permanecer en almacenamiento privado. Videos largos consumen memoria porque flet-camera devuelve los bytes de la captura: para la exposición usa clips breves. Borrar los datos o desinstalar la aplicación elimina los registros. La extensión de cámara no admite Windows: allí el formulario muestra un aviso y permite continuar con el resto de funciones. Otros servicios dependen del hardware y sistema; se informa el error. La ejecución web no es el destino de esta entrega.

## Demostración manual

1. Abrir Inicio y recorrer las cuatro secciones.
2. En Reportar, activar cámara, tomar foto, grabar y detener un video breve; reproducirlo. Grabar/detener y reproducir voz.
3. Obtener GPS y comprobar coordenadas. Denegar un permiso y apagar GPS para comprobar mensajes.
4. Guardar con descripción vacía y sin coordenadas para comprobar validaciones; completar y guardar.
5. Abrir Historial, seleccionar el registro y reproducir sus evidencias.
6. Cerrar por completo y volver a abrir: comprobar que el registro y sus evidencias permanecen.
7. Abrir Mapa, seleccionar el marcador, elegir otro punto, registrar allí y volver a centrar en el usuario.
8. Desconectar Internet y abrir una zona sin teselas disponibles: verificar aviso de error.
