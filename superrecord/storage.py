"""
Storage custom para WhiteNoise: usa hash en el nombre de archivo
(pos-dark.a3f5b2.css) para que cada deploy invalide la cache del navegador
automaticamente sin requerir Ctrl+Shift+R.

manifest_strict=False evita que un referencia a un archivo inexistente
(por ejemplo un url() en un CSS apuntando a una imagen que ya no esta)
tire abajo todo el collectstatic.

Override url(): HashedFilesMixin.url() retorna el nombre sin hashear cuando
DEBUG=True. En produccion, si DEBUG quedo mal configurado (caso real en Railway),
las URLs salen sin hash y la cache del navegador sirve archivos viejos tras un
deploy. Forzamos force=True para ignorar DEBUG: el cache-busting por hash es
correcto incluso en dev, y evita que un DEBUG mal seteado rompa produccion.
"""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def url(self, name, force=False):
        return super().url(name, force=True)
