<template>
  <button
    class="custom-icon-btn btn-delete-custom"
    type="button"
    :title="title"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <img :src="deleteIcon" alt="Удалить" class="custom-icon-img" />
  </button>
</template>

<script setup>
import deleteIcon from '@/assets/icons/delete.png'

defineProps({
  title: {
    type: String,
    default: 'Удалить'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])
</script>

<style scoped>
.custom-icon-btn {
  min-width: 32px;
  width: 32px;
  height: 32px;
  padding: 4px;
  border: none;
  border-radius: 4px;
  background: transparent;
  box-shadow: none;
  cursor: pointer;
  opacity: 1; /* всегда видна */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  transition: background-color 0.15s ease, transform 0.2s ease;
}

.custom-icon-btn:hover {
  background: rgba(244, 67, 54, 0.12);
  transform: scale(1.15);
}

.custom-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

.custom-icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.custom-icon-btn:disabled:hover {
  background: transparent;
  transform: none;
}
</style>
