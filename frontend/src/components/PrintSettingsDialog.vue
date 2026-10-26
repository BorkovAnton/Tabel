<template>
  <v-dialog v-model="show" max-width="600">
    <v-card>
      <v-card-title>
        <v-icon class="mr-2">mdi-printer-settings</v-icon>
        Настройки печати Т-13
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          Выберите итоговые колонки, которые будут отображаться в печатной форме.
          Настройки сохраняются персонально для вас.
        </v-alert>

        <v-checkbox
          v-for="col in allColumns"
          :key="col.key"
          v-model="selectedColumns"
          :value="col.key"
          :label="col.label"
          color="primary"
          density="compact"
          hide-details
          class="mb-1"
        />

        <div class="d-flex mt-4" style="gap: 8px;">
          <v-btn variant="text" size="small" @click="selectAll">Выбрать все</v-btn>
          <v-btn variant="text" size="small" @click="selectNone">Снять все</v-btn>
          <v-btn variant="text" size="small" @click="selectDefault">По умолчанию</v-btn>
        </div>

        <v-alert v-if="error" type="error" density="compact" class="mt-3">
          {{ error }}
        </v-alert>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="show = false">Отмена</v-btn>
        <v-btn color="primary" :loading="saving" @click="save">Сохранить</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../api'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'saved'])

const show = ref(props.modelValue)
const selectedColumns = ref([])
const saving = ref(false)
const error = ref('')

// Все 13 итоговых колонок печатной формы Т-13
// (ключи должны совпадать с summaryColumns в utils/tabelCalculations.js
// и с ALL_COLUMNS на бэкенде — app/api/user_print_settings.py)
const allColumns = [
  { key: 'fact_days', label: 'фактической работы (дни)' },
  { key: 'vacation', label: 'трудовой отпуск' },
  { key: 'sick', label: 'болезнь' },
  { key: 'admin_leave', label: 'с разрешения администрации' },
  { key: 'weekend_holiday', label: 'выходные и праздн.' },
  { key: 'other_absence', label: 'Другие неявки' },
  { key: 'overtime_days', label: 'сверхурочные дни' },
  { key: 'overtime_total', label: 'Сверхурочные часы итого (часы + дни)' },
  { key: 'overtime_hours', label: 'Сверхурочные часы без дней (только часы)' },
  { key: 'night_hours', label: 'ночные часы' },
  { key: 'kdu_work_days', label: 'КДУ' },
  { key: 'kdu_weekend_days', label: 'КДУ вых. дня' },
  { key: 'tariff_hours', label: 'Часы по тарифу' },
  // «Итого часов» — в конце (в печатной форме крайняя справа, шире в 1.5 раза)
  { key: 'total_hours', label: 'Итого часов' }
]

const defaultColumns = ['fact_days', 'total_hours', 'vacation', 'sick', 'overtime_total', 'overtime_hours', 'tariff_hours']

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val) {
    error.value = ''
    loadSettings()
  }
})

watch(show, (val) => {
  emit('update:modelValue', val)
})

async function loadSettings() {
  try {
    const { data } = await api.get('/api/user-print-settings/')
    // Пустой/отсутствующий список → показать все колонки
    selectedColumns.value = (data.selected_columns && data.selected_columns.length)
      ? [...data.selected_columns]
      : allColumns.map(c => c.key)
  } catch (e) {
    console.error('Ошибка загрузки настроек:', e)
    // Не удалось загрузить — показываем все колонки
    selectedColumns.value = allColumns.map(c => c.key)
  }
}

async function save() {
  if (selectedColumns.value.length === 0) {
    error.value = 'Выберите хотя бы одну колонку'
    return
  }

  saving.value = true
  error.value = ''

  try {
    await api.put('/api/user-print-settings/', {
      selected_columns: selectedColumns.value
    })
    emit('saved', [...selectedColumns.value])
    show.value = false
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка сохранения'
  } finally {
    saving.value = false
  }
}

function selectAll() {
  selectedColumns.value = allColumns.map(c => c.key)
}

function selectNone() {
  selectedColumns.value = []
}

function selectDefault() {
  selectedColumns.value = [...defaultColumns]
}
</script>
