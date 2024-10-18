import hashlib
import uuid

from django.apps import apps


class UniqueId:

    @staticmethod
    def generate_id():
        unique_id = str(uuid.uuid4())
        while UniqueId.check_id(unique_id):
            unique_id = str(uuid.uuid4())
        return unique_id

    @staticmethod
    def check_id(uniqueId: str):
        app_labels = ["users", "order"]
        for app_label in app_labels:
            apps_models = apps.get_app_config(app_label).get_models()
            for model in apps_models:
                for field in model._meta.fields:
                    if field.name in ["slug", "reference"]:
                        if model.objects.filter(**{field.name: uniqueId}).exists():
                            return True
        return False


def device_id(request):
    user_agent = request.META.get("HTTP_USER_AGENT", "unknown")
    ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
    raw_string = f"{user_agent}_{ip_address}_{uuid.uuid4()}"
    device_id = int(hashlib.md5(raw_string.encode("utf-8")).hexdigest(), 16) % (10**8)

    return device_id
