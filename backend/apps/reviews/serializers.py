from django.db import transaction
from rest_framework import serializers

from apps.menu.serializers import DishSerializer
from apps.orders.models import Order

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    dish_detail = DishSerializer(source="dish", read_only=True)
    is_updated = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "order",
            "dish",
            "dish_detail",
            "student_name",
            "rating",
            "content",
            "created_at",
            "updated_at",
            "is_updated",
        ]
        read_only_fields = ["created_at", "updated_at"]
        validators = []

    def get_is_updated(self, obj):
        return obj.updated_at and obj.updated_at.replace(microsecond=0) > obj.created_at.replace(microsecond=0)

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("评分必须在 1 到 5 之间。")
        return value

    def validate(self, attrs):
        order = attrs.get("order")
        dish = attrs.get("dish")
        student_name = attrs.get("student_name")

        if not order:
            raise serializers.ValidationError({"order": "必须关联订单才能评价。"})

        try:
            order = Order.objects.select_related("delivery").prefetch_related("items__dish").get(id=order.id)
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order": "订单不存在。"})

        if order.status == "cancelled":
            raise serializers.ValidationError({"order": "已取消的订单不能评价。"})

        if order.payment_status == "unpaid":
            raise serializers.ValidationError({"order": "未支付的订单不能评价。"})

        if order.status != "completed":
            raise serializers.ValidationError({"order": "只有已完成的订单才能评价。"})

        if hasattr(order, "delivery") and order.delivery.status == "failed":
            raise serializers.ValidationError({"order": "配送异常未关闭的订单不能评价。"})

        order_dish_ids = order.items.values_list("dish_id", flat=True)
        if dish.id not in order_dish_ids:
            raise serializers.ValidationError({"dish": "该菜品不在此订单中，无法评价。"})

        if student_name != order.student_name:
            raise serializers.ValidationError(
                {"student_name": f"评价人姓名必须与订单下单人「{order.student_name}」一致。"}
            )

        attrs["order"] = order
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        existing = Review.objects.filter(
            order=validated_data["order"],
            dish=validated_data["dish"],
            student_name=validated_data["student_name"],
        ).first()
        if existing:
            existing.rating = validated_data["rating"]
            existing.content = validated_data["content"]
            existing.save(update_fields=["rating", "content", "updated_at"])
            return existing
        return super().create(validated_data)
