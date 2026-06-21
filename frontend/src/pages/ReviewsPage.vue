<template>
  <div class="reviews-layout">
    <section class="panel">
      <div class="panel-title">
        <h2>提交评价</h2>
      </div>
      <form class="order-form" @submit.prevent="submitReview">
        <label>
          订单
          <select v-model="form.order" required @change="onOrderChange">
            <option value="">请选择已完成的订单</option>
            <option v-for="order in eligibleOrders" :key="order.id" :value="order.id">
              #{{ order.id }} - {{ order.student_name }} - {{ formatDate(order.created_at) }}
            </option>
          </select>
        </label>
        <label>
          菜品
          <select v-model="form.dish" required :disabled="!orderDishes.length">
            <option value="">请选择菜品</option>
            <option v-for="dish in orderDishes" :key="dish.id" :value="dish.id">
              {{ dish.name }}
              <template v-if="dish.avg_rating">（当前均分 {{ dish.avg_rating.toFixed(1) }}，{{ dish.review_count }} 人评价）</template>
            </option>
          </select>
        </label>
        <label>
          姓名
          <input v-model="form.student_name" readonly placeholder="选择订单后自动填充" />
        </label>
        <label>
          评分
          <div class="rating-input">
            <span class="star-display">{{ '★'.repeat(form.rating) }}{{ '☆'.repeat(5 - form.rating) }}</span>
            <input v-model.number="form.rating" max="5" min="1" required type="range" />
          </div>
        </label>
        <label>
          评价内容
          <textarea v-model="form.content" required rows="5" placeholder="口味、分量、配送体验等"></textarea>
        </label>
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>
        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? '提交中...' : '提交评价' }}
        </button>
      </form>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h2>近期反馈</h2>
        <span>{{ reviews.length }} 条</span>
      </div>
      <div class="review-list">
        <article v-for="review in reviews" :key="review.id" class="review-card">
          <div>
            <strong>{{ review.dish_detail.name }}</strong>
            <span>{{ '★'.repeat(review.rating) }}</span>
            <em v-if="review.is_updated" class="updated-tag">已更新</em>
          </div>
          <p>{{ review.content }}</p>
          <small>{{ review.student_name }} · {{ formatDate(review.created_at) }}</small>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { createReview, fetchDishes, fetchOrders, fetchReviews } from '../api/canteen'

const props = defineProps({
  reloadKey: {
    type: Number,
    default: 0,
  },
})

const allOrders = ref([])
const dishes = ref([])
const reviews = ref([])
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const form = reactive({
  order: '',
  dish: '',
  student_name: '',
  rating: 5,
  content: '',
})

const eligibleOrders = computed(() =>
  allOrders.value.filter((o) => o.status === 'completed' && o.payment_status === 'paid'),
)

const orderDishes = computed(() => {
  if (!form.order) return []
  const order = allOrders.value.find((o) => o.id === Number(form.order))
  if (!order) return []
  const dishIds = order.items.map((item) => item.dish)
  return dishes.value.filter((d) => dishIds.includes(d.id))
})

function onOrderChange() {
  form.dish = ''
  form.student_name = ''
  const order = allOrders.value.find((o) => o.id === Number(form.order))
  if (order) {
    form.student_name = order.student_name
  }
  errorMessage.value = ''
  successMessage.value = ''
}

async function loadData() {
  const [dishData, orderData, reviewData] = await Promise.all([
    fetchDishes(),
    fetchOrders(),
    fetchReviews(),
  ])
  dishes.value = dishData
  allOrders.value = orderData
  reviews.value = reviewData
}

async function submitReview() {
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = {
      order: Number(form.order),
      dish: Number(form.dish),
      student_name: form.student_name,
      rating: form.rating,
      content: form.content,
    }
    await createReview(payload)
    const existing = reviews.value.find(
      (r) =>
        r.order === payload.order &&
        r.dish === payload.dish &&
        r.student_name === payload.student_name,
    )
    successMessage.value = existing ? '评价已更新，感谢您的反馈！' : '评价提交成功，感谢您的反馈！'
    form.content = ''
    form.rating = 5
    await loadData()
  } catch (err) {
    const detail = err?.response?.data
    if (detail) {
      const parts = []
      for (const [key, val] of Object.entries(detail)) {
        const label = {
          order: '订单',
          dish: '菜品',
          student_name: '评价人',
          rating: '评分',
          content: '评价内容',
          non_field_errors: '',
        }[key] || key
        const msg = Array.isArray(val) ? val.join('；') : val
        parts.push(label ? `${label}：${msg}` : msg)
      }
      errorMessage.value = parts.join('\n')
    } else {
      errorMessage.value = '提交失败，请稍后重试。'
    }
  } finally {
    submitting.value = false
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(loadData)
watch(() => props.reloadKey, loadData)
</script>

<style scoped>
.rating-input {
  display: flex;
  align-items: center;
  gap: 12px;
}
.star-display {
  font-size: 22px;
  color: #f5a623;
  min-width: 120px;
}
.error-message {
  color: #c0392b;
  background: #fdecea;
  border: 1px solid #f5c2be;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  white-space: pre-wrap;
}
.success-message {
  color: #1e8449;
  background: #eafaf1;
  border: 1px solid #abebc6;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
}
.updated-tag {
  font-style: normal;
  font-size: 12px;
  color: #888;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 6px;
}
</style>
