<template>
  <button
    class="custom-icon-btn btn-edit-custom"
    type="button"
    :title="title"
    @click="$emit('click')"
  >
    <img :src="editIcon" alt="Редактировать" class="custom-icon-img" />
  </button>
</template>

<script setup>
import editIcon from '@/assets/icons/edit.png'

defineProps({
  title: {
    type: String,
    default: 'Редактировать'
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
  background: rgba(0, 0, 0, 0.08);
  /* Лёгкое увеличение вместо сильного — transform на inline-элементах
     может «прыгать» в таблицах; при необходимости верните scale(1.1) */
  transform: scale(1.1);
}

.custom-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
  display: block;
  pointer-events: none;
}
</style>
