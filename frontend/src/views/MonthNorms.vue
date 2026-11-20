<template>
  <v-container>
    <h1 class="text-h4 mb-4">Нормы рабочего времени по месяцам</h1>
    
    <div class="mb-4 d-flex align-center" style="gap: 12px; flex-wrap: wrap;">
      <v-text-field
        v-model.number="yearInput"
        label="Год"
        type="number"
        variant="outlined"
        density="compact"
        hide-details
        style="max-width: 120px;"
        @change="loadNorms"
      ></v-text-field>

      <v-btn color="success" @click="autoCalculate" :loading="calculating" prepend-icon="mdi-calculator">
        Рассчитать нормы на {{ yearInput }} год
      </v-btn>
      <v-btn color="primary" @click="openAddDialog" prepend-icon="mdi-plus">
        Добавить вручную
      </v-btn>
    </div>
    
    <v-table>
      <thead>
        <tr>
          <th>Год</th>
          <th>Месяц</th>
          <th>Норма часов</th>
          <th>Рабочих дней</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="norm in norms" :key="norm.id">
          <td>{{ norm.year }}</td>
          <td>{{ monthNames[norm.month - 1] }}</td>
          <td>{{ norm.norm_hours }}</td>
          <td>{{ norm.working_days }}</td>
          <td>
            <v-btn icon @click="openEditDialog(norm)" class="mr-2" size="small">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
            <v-btn icon @click="deleteNorm(norm.id)" color="error" size="small">
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    
    <!-- Диалог добавления/редактирования -->
    <v-dialog v-model="dialog" max-width="500">
      <v-card>
        <v-card-title>{{ isEdit ? 'Редактировать' : 'Добавить' }} норму</v-card-title>
        <v-card-text>
          <v-text-field 
            v-model="form.year" 
            label="Год" 
            type="number" 
            variant="outlined" 
            class="mb-4"
          ></v-text-field>
          <v-select 
            v-model="form.month" 
            :items="monthItems" 
            label="Месяц" 
            variant="outlined" 
            class="mb-4"
          ></v-select>
          <v-text-field 
            v-model="form.norm_hours" 
            label="Норма часов" 
            type="number" 
            step="0.1"
            variant="outlined" 
            class="mb-4"
          ></v-text-field>
          <v-text-field 
            v-model="form.working_days" 
            label="Рабочих дней" 
            type="number" 
            variant="outlined"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="dialog = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveNorm" :loading="saving">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const norms = ref([])
const dialog = ref(false)
const isEdit = ref(false)
const calculating = ref(false)
const yearInput = ref(new Date().getFullYear())

const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
const monthItems = monthNames.map((name, i) => ({ title: name, value: i + 1 }))

const form = ref({
  year: 2026,
  month: 1,
  norm_hours: 0,
  working_days: 0
})

async function loadNorms() {
  try {
    const { data } = await api.get('/month-norms/', { params: { year: yearInput.value } })
    norms.value = data
  } catch (e) {
    console.error('Ошибка загрузки норм:', e)
  }
}

async function autoCalculate() {
  calculating.value = true
  try {
    const { data } = await api.post('/month-norms/auto-calculate', null, {
      params: { year: yearInput.value }
    })
    alert(data.message)
    await loadNorms()
  } catch (e) {
    console.error('Ошибка авторасчёта:', e)
    alert(e.response?.data?.detail || 'Ошибка при расчёте')
  } finally {
    calculating.value = false
  }
}

function openAddDialog() {
  isEdit.value = false
  selectedNorm.value = null
  form.value = { year: 2026, month: 1, norm_hours: 0, working_days: 0 }
  dialog.value = true
}

function openEditDialog(norm) {
  isEdit.value = true
  selectedNorm.value = norm
  form.value = { ...norm }
  dialog.value = true
}

async function saveNorm() {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/month-norms/${selectedNorm.value.id}`, form.value)
    } else {
      await api.post('/month-norms/', form.value)
    }
    dialog.value = false
    await loadNorms()
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert(e.response?.data?.detail || 'Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

async function deleteNorm(id) {
  if (!confirm('Удалить норму?')) return
  try {
    await api.delete(`/month-norms/${id}`)
    await loadNorms()
  } catch (e) {
    console.error('Ошибка удаления:', e)
    alert('Ошибка при удалении')
  }
}

onMounted(loadNorms)
</script>