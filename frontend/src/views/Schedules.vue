<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h4 font-weight-bold mb-6">Графики работы</h1>

    <v-btn color="primary" class="mb-4" @click="openAddDialog" prepend-icon="mdi-plus">
      Добавить график
    </v-btn>

    <v-row>
      <v-col cols="12" md="6" v-for="schedule in schedules" :key="schedule.id">
        <v-card elevation="2" class="pa-4">
          <div class="d-flex justify-space-between align-center mb-3">
            <h3 class="text-h6 font-weight-bold">{{ schedule.name }}</h3>
            <div>
              <v-btn icon size="small" @click="openEditDialog(schedule)" class="mr-2">
                <v-icon>mdi-pencil</v-icon>
              </v-btn>
              <v-btn icon size="small" color="error" @click="confirmDelete(schedule)">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </div>
          </div>

          <v-chip color="blue" class="mb-3">
            Норма в неделю: {{ schedule.week_norm_hours }} ч
          </v-chip>
          <v-chip color="grey" class="ml-2 mb-3">
            Сотрудников: {{ schedule.employee_count }}
          </v-chip>

          <v-table density="compact">
            <thead>
              <tr>
                <th>День</th>
                <th>Начало</th>
                <th>Конец</th>
                <th>Обед</th>
                <th>Норма</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="day in schedule.days" :key="day.day_of_week"
                  :class="{ 'bg-grey-lighten-4': day.is_day_off }">
                <td class="font-weight-medium">{{ day.day_name }}</td>
                <td>{{ day.start_time || '-' }}</td>
                <td>{{ day.end_time || '-' }}</td>
                <td>{{ day.is_day_off ? '-' : day.lunch_minutes + ' мин' }}</td>
                <td>
                  <v-chip :color="day.is_day_off ? 'grey' : 'green'" size="small">
                    {{ day.norm_hours }} ч
                  </v-chip>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Диалог -->
    <v-dialog v-model="dialog" max-width="800">
      <v-card>
        <v-card-title>{{ isEdit ? 'Редактировать' : 'Добавить' }} график работы</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="scheduleName"
            label="Название графика"
            variant="outlined"
            class="mb-4"
          ></v-text-field>

          <v-table density="compact">
            <thead>
              <tr>
                <th>День</th>
                <th>Выходной</th>
                <th>Начало</th>
                <th>Конец</th>
                <th>Обед (мин)</th>
                <th>Норма</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(day, idx) in days" :key="idx">
                <td class="font-weight-medium">{{ day.day_name }}</td>
                <td>
                  <v-checkbox v-model="day.is_day_off" color="primary" hide-details density="compact"></v-checkbox>
                </td>
                <td>
                  <v-text-field
                    v-model="day.start_time"
                    type="time"
                    :disabled="day.is_day_off"
                    density="compact"
                    hide-details
                  ></v-text-field>
                </td>
                <td>
                  <v-text-field
                    v-model="day.end_time"
                    type="time"
                    :disabled="day.is_day_off"
                    density="compact"
                    hide-details
                  ></v-text-field>
                </td>
                <td>
                  <v-text-field
                    v-model.number="day.lunch_minutes"
                    type="number"
                    :disabled="day.is_day_off"
                    density="compact"
                    hide-details
                    min="0"
                  ></v-text-field>
                </td>
                <td>
                  <v-chip :color="day.is_day_off ? 'grey' : 'green'" size="small">
                    {{ calculateDayNorm(day) }} ч
                  </v-chip>
                </td>
              </tr>
            </tbody>
          </v-table>

          <v-alert type="info" variant="tonal" class="mt-4">
            Итого норма в неделю: <strong>{{ weekNorm }} ч</strong>
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="dialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveSchedule" :loading="saving">
            Сохранить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог удаления -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Подтверждение удаления</v-card-title>
        <v-card-text>
          Удалить график "{{ selectedSchedule?.name }}"?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="deleteDialog = false">Отмена</v-btn>
          <v-btn color="error" @click="deleteSchedule" :loading="deleting">
            Удалить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const DAY_NAMES = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const schedules = ref([])
const dialog = ref(false)
const deleteDialog = ref(false)
const isEdit = ref(false)
const selectedSchedule = ref(null)
const scheduleName = ref('')
const days = ref([])

function emptyDay(day_of_week) {
  return {
    day_of_week,
    day_name: DAY_NAMES[day_of_week],
    start_time: '08:00',
    end_time: '17:00',
    lunch_minutes: 60,
    is_day_off: day_of_week >= 5  // Сб и Вс по умолчанию выходные
  }
}

function initDays() {
  days.value = Array.from({ length: 7 }, (_, i) => emptyDay(i))
}

function calculateDayNorm(day) {
  if (day.is_day_off || !day.start_time || !day.end_time) return 0
  const [sh, sm] = day.start_time.split(':').map(Number)
  const [eh, em] = day.end_time.split(':').map(Number)
  let startMin = sh * 60 + sm
  let endMin = eh * 60 + em
  if (endMin <= startMin) endMin += 24 * 60
  const gross = (endMin - startMin) / 60
  return Math.max(gross - day.lunch_minutes / 60, 0).toFixed(2)
}

const weekNorm = computed(() => {
  return days.value.reduce((sum, d) => sum + parseFloat(calculateDayNorm(d)), 0).toFixed(2)
})

async function loadSchedules() {
  loading.value = true
  try {
    const response = await api.get('/schedules/')
    schedules.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки графиков:', e)
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  isEdit.value = false
  selectedSchedule.value = null
  scheduleName.value = ''
  initDays()
  dialog.value = true
}

function openEditDialog(item) {
  isEdit.value = true
  selectedSchedule.value = item
  scheduleName.value = item.name
  days.value = item.days.map(d => ({
    day_of_week: d.day_of_week,
    day_name: d.day_name,
    start_time: d.start_time || '08:00',
    end_time: d.end_time || '17:00',
    lunch_minutes: d.lunch_minutes,
    is_day_off: d.is_day_off
  }))
  dialog.value = true
}

async function saveSchedule() {
  if (!scheduleName.value.trim()) {
    alert('Введите название графика')
    return
  }

  saving.value = true
  try {
    const data = {
      name: scheduleName.value,
      days: days.value.map(d => ({
        day_of_week: d.day_of_week,
        start_time: d.is_day_off ? null : d.start_time,
        end_time: d.is_day_off ? null : d.end_time,
        lunch_minutes: d.lunch_minutes,
        is_day_off: d.is_day_off
      }))
    }

    if (isEdit.value) {
      await api.patch(`/schedules/${selectedSchedule.value.id}`, data)
    } else {
      await api.post('/schedules/', data)
    }
    dialog.value = false
    await loadSchedules()
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert(e.response?.data?.detail || 'Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  selectedSchedule.value = item
  deleteDialog.value = true
}

async function deleteSchedule() {
  deleting.value = true
  try {
    await api.delete(`/schedules/${selectedSchedule.value.id}`)
    deleteDialog.value = false
    await loadSchedules()
  } catch (e) {
    console.error('Ошибка удаления:', e)
    alert(e.response?.data?.detail || 'Ошибка при удалении')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadSchedules()
})
</script>

<style>
/* Глобальные стили для чекбоксов в таблице графиков */

/* Основной контейнер чекбокса */
.v-checkbox-btn {
  opacity: 1 !important;
}

/* Рамка чекбокса */
.v-checkbox-btn .v-selection-control__wrapper {
  border: 2px solid #1976d2 !important;
  border-radius: 4px !important;
  background-color: white !important;
}

/* Иконка (круг внутри) */
.v-checkbox-btn .v-selection-control__input {
  color: #1976d2 !important;
  background-color: transparent !important;
  width: 20px !important;
  height: 20px !important;
}

/* Выбранный чекбокс — синий фон */
.v-checkbox-btn.v-selection-control--dirty .v-selection-control__wrapper {
  background-color: #1976d2 !important;
  border-color: #1565c0 !important;
}

/* Галочка в выбранном чекбоксе — белая */
.v-checkbox-btn.v-selection-control--dirty .v-selection-control__input .v-icon {
  color: white !important;
  opacity: 1 !important;
}

/* Hover эффект */
.v-checkbox-btn:hover .v-selection-control__wrapper {
  border-color: #1565c0 !important;
  background-color: rgba(25, 118, 210, 0.08) !important;
}

/* Чекбокс в таблице — выравнивание */
.v-table td .v-checkbox-btn {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}
</style>