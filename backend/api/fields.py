from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers


class RequiredBase64ImageField(Base64ImageField):
    """Принимает Base64-изображение и запрещает пустое значение."""

    def to_internal_value(self, data):
        if data in self.EMPTY_VALUES:
            raise serializers.ValidationError(
                'Изображение не может быть пустым.'
            )
        return super().to_internal_value(data)
