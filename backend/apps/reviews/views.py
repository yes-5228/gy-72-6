from django.db import IntegrityError, transaction
from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("dish__category", "order").all()
    serializer_class = ReviewSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["student_name", "content", "dish__name"]
    ordering_fields = ["created_at", "rating"]

    def get_queryset(self):
        queryset = super().get_queryset()
        dish = self.request.query_params.get("dish")
        if dish:
            queryset = queryset.filter(dish_id=dish)
        order = self.request.query_params.get("order")
        if order:
            queryset = queryset.filter(order_id=order)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = serializer.save()
        except IntegrityError:
            existing = Review.objects.filter(
                order_id=request.data.get("order"),
                dish_id=request.data.get("dish"),
                student_name=request.data.get("student_name"),
            ).first()
            if existing:
                existing.rating = request.data.get("rating", existing.rating)
                existing.content = request.data.get("content", existing.content)
                existing.save(update_fields=["rating", "content", "updated_at"])
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)
            raise
        created = instance.created_at == instance.updated_at or (
            instance.updated_at and instance.updated_at.replace(microsecond=0) == instance.created_at.replace(microsecond=0)
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            headers=headers,
        )
