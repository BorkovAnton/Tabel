<template>
  <button
    class="btn-edit-custom"
    type="button"
    :title="title"
    @click="$emit('click')"
  >
    <img :src="editIcon" alt="Редактировать" />
  </button>
</template>

<script setup>
import editIcon from '../assets/icons/edit.png'

defineProps({
  title: {
    type: String,
    default: 'Редактировать'
  }
})

defineEmits(['click'])
</script>
