<template>
  <button
    class="btn-delete-custom"
    type="button"
    :title="title"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <img :src="deleteIcon" alt="Удалить" />
  </button>
</template>

<script setup>
import deleteIcon from '../assets/icons/delete.png'

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
.btn-delete-custom:disabled {
  cursor: not-allowed;
  opacity: 0.4 !important;
}

.btn-delete-custom:disabled:hover {
  transform: none;
}
</style>
