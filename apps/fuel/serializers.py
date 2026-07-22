from rest_framework import serializers


class RoutePlanningSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=255)
    end = serializers.CharField(max_length=255, required=False)
    finish = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        end = (attrs.get("end") or attrs.get("finish") or "").strip()
        start = attrs.get("start", "").strip()

        if not start or not end:
            raise serializers.ValidationError("Both start and end/finish are required.")

        attrs["start"] = start
        attrs["end"] = end
        return attrs
