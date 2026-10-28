from aioinject import Scoped, Singleton

from common.files.storage import FileStorage, LocalFileStorage
from managers.attachments.mng_attachments import AttachmentManager
from services.attachments.svc_attachments import AttachmentService
from services.di.types import Providers

providers: Providers = [
    Singleton(LocalFileStorage, interface=FileStorage),
    Scoped(AttachmentManager),
    Scoped(AttachmentService),
]
