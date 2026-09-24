<template>
  <div style="padding: 20px;">
    <h1 style="font-size: 24px; font-weight: bold; margin-bottom: 20px;">Сотрудники</h1>

    <button 
      @click="openAddDialog" 
      style="background: #1976d2; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 20px; font-size: 14px;"
    >
      + Добавить сотрудника
    </button>

    <div v-if="error" style="background: #ffebee; color: #c62828; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; border: 1px solid #ffcdd2;">
      {{ error }}
      <button @click="error = ''" style="float: right; background: none; border: none; cursor: pointer; font-size: 18px;">×</button>
    </div>

    <div v-if="loading" style="padding: 20px; text-align: center;">Загрузка...</div>
    
    <div v-else-if="employees.length === 0" style="padding: 20px; text-align: center; color: gray;">
      Нет сотрудников
    </div>
    
    <div v-else style="border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
      <!-- Заголовок таблицы -->
      <div style="display: flex; background: #f5f5f5; border-bottom: 2px solid #e0e0e0; font-weight: bold;">
        <div style="width: 60px; padding: 10px; border-right: 1px solid #e0e0e0;">ID</div>
        <div style="width: 100px; padding: 10px; border-right: 1px solid #e0e0e0;">Таб. номер</div>
        <div style="flex: 1; padding: 10px; border-right: 1px solid #e0e0e0;">Ф.И.О.</div>
        <div style="flex: 1; padding: 10px; border-right: 1px solid #e0e0e0;">Подразделение</div>
        <div style="width: 180px; padding: 10px; border-right: 1px solid #e0e0e0;">График</div>
        <div style="width: 100px; padding: 10px; text-align: center;">Действия</div>
      </div>
      
      <!-- Строки таблицы -->
      <div 
        v-for="emp in paginatedEmployees" 
        :key="emp.id"
        style="display: flex; border-bottom: 1px solid #f0f0f0; transition: background-color 0.2s;"
        @mouseenter="$event.currentTarget.style.backgroundColor = '#f5f5f5'"
        @mouseleave="$event.currentTarget.style.backgroundColor = 'transparent'"
      >
        <div style="width: 60px; padding: 10px; border-right: 1px solid #f0f0f0;">{{ emp.id }}</div>
        <div style="width: 100px; padding: 10px; border-right: 1px solid #f0f0f0;">{{ emp.tab_number }}</div>
        <div style="flex: 1; padding: 10px; border-right: 1px solid #f0f0f0;">{{ emp.full_name }}</div>
        <div style="flex: 1; padding: 10px; border-right: 1px solid #f0f0f0;">{{ emp.department_name || '-' }}</div>
        <div style="width: 180px; padding: 10px; border-right: 1px solid #f0f0f0;">
          <span v-if="emp.schedule_id" style="background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 12px; font-size: 12px;">
            {{ getScheduleName(emp.schedule_id) }}
          </span>
          <span v-else style="color: gray;">-</span>
        </div>
        <div style="width: 100px; padding: 10px; text-align: center;">
          <button 
            @click="openEditDialog(emp)"
            style="background: none; border: none; cursor: pointer; margin-right: 4px; font-size: 18px;"
            title="Редактировать"
          >
            ✏️
          </button>
          <button 
            @click="confirmDelete(emp)"
            style="background: none; border: none; cursor: pointer; font-size: 18px;"
            title="Удалить"
          >
            ️
          </button>
        </div>
      </div>
      
      <!-- Пагинация -->
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #fafafa;">
        <div style="font-size: 13px; color: gray;">
          Показано {{ startIndex + 1 }}-{{ endIndex }} из {{ employees.length }}
        </div>
        
        <div style="display: flex; gap: 4px;">
          <button 
            @click="currentPage--"
            :disabled="currentPage === 1"
            :style="{
              padding: '6px 12px',
              border: '1px solid #1976d2',
              background: currentPage === 1 ? '#f5f5f5' : '#1976d2',
              color: currentPage === 1 ? '#999' : 'white',
              borderRadius: '4px',
              cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
              fontSize: '13px'
            }"
          >
            ← Назад
          </button>
          
          <button 
            v-for="page in visiblePages" 
            :key="page"
            @click="currentPage = page"
            :style="{
              padding: '6px 12px',
              border: '1px solid #1976d2',
              background: currentPage === page ? '#1976d2' : 'white',
              color: currentPage === page ? 'white' : '#1976d2',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: currentPage === page ? 'bold' : 'normal'
            }"
          >
            {{ page }}
          </button>
          
          <button 
            @click="currentPage++"
            :disabled="currentPage === totalPages"
            :style="{
              padding: '6px 12px',
              border: '1px solid #1976d2',
              background: currentPage === totalPages ? '#f5f5f5' : '#1976d2',
              color: currentPage === totalPages ? '#999' : 'white',
              borderRadius: '4px',
              cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
              fontSize: '13px'
            }"
          >
            Вперёд →
          </button>
        </div>
        
        <div style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <span>На странице:</span>
          <select 
            v-model.number="itemsPerPage"
            @change="currentPage = 1"
            style="padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px;"
          >
            <option :value="10">10</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Диалог добавления/редактирования -->
    <div v-if="dialog" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
      <div style="background: white; padding: 30px; border-radius: 8px; min-width: 450px; max-width: 90vw;">
        <h2 style="margin-top: 0; margin-bottom: 20px;">{{ isEdit ? 'Редактировать' : 'Добавить' }} сотрудника</h2>
        
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">Табельный номер *</label>
          <input 
            v-model="tabNumber" 
            type="text" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
          />
        </div>
        
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">Ф.И.О. *</label>
          <input 
            v-model="fullName" 
            type="text" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
          />
        </div>
        
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">Подразделение</label>
          <select 
            v-model="departmentId" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
          >
            <option :value="null">-- Не выбрано --</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
            </option>
          </select>
        </div>
        
        <div style="margin-bottom: 20px;">
          <label style="display: block; margin-bottom: 5px; font-weight: bold;">График работы</label>
          <select 
            v-model="scheduleId" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
          >
            <option :value="null">-- Не выбран --</option>
            <option v-for="sched in schedules" :key="sched.id" :value="sched.id">
              {{ sched.name }}
            </option>
          </select>
        </div>
        
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button 
            @click="dialog = false"
            style="padding: 8px 16px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;"
          >
            Отмена
          </button>
          <button 
            @click="saveEmployee"
            :disabled="saving"
            style="padding: 8px 16px; border: none; background: #1976d2; color: white; border-radius: 4px; cursor: pointer;"
          >
            {{ saving ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Диалог подтверждения удаления -->
    <div v-if="deleteDialog" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
      <div style="background: white; padding: 30px; border-radius: 8px; min-width: 400px;">
        <h2 style="margin-top: 0;">Подтверждение удаления</h2>
        <p>Вы уверены, что хотите удалить сотрудника "{{ selectedEmployee?.full_name }}"?</p>
        
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button 
            @click="deleteDialog = false"
            style="padding: 8px 16px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;"
          >
            Отмена
          </button>
          <button 
            @click="deleteEmployee"
            :disabled="deleting"
            style="padding: 8px 16px; border: none; background: #d32f2f; color: white; border-radius: 4px; cursor: pointer;"
          >
            {{ deleting ? 'Удаление...' : 'Удалить' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const employees = ref([])
const departments = ref([])
const schedules = ref([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const error = ref('')
const dialog = ref(false)
const deleteDialog = ref(false)
const isEdit = ref(false)
const selectedEmployee = ref(null)
const tabNumber = ref('')
const fullName = ref('')
const departmentId = ref(null)
const scheduleId = ref(null)
const itemsPerPage = ref(10)
const currentPage = ref(1)

// Вычисляемые свойства для пагинации
const totalPages = computed(() => Math.ceil(employees.value.length / itemsPerPage.value))

const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage.value)
const endIndex = computed(() => Math.min(startIndex.value + itemsPerPage.value, employees.value.length))

const paginatedEmployees = computed(() => {
  return employees.value.slice(startIndex.value, endIndex.value)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  // Показываем максимум 5 страниц вокруг текущей
  let start = Math.max(1, current - 2)
  let end = Math.min(total, current + 2)
  
  // Корректируем, если нужно показать 5 страниц
  if (end - start < 4) {
    if (start === 1) {
      end = Math.min(total, start + 4)
    } else {
      start = Math.max(1, end - 4)
    }
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

function getScheduleName(scheduleId) {
  if (!scheduleId) return '-'
  const schedule = schedules.value.find(s => s.id === scheduleId)
  return schedule ? schedule.name : `График ${scheduleId}`
}

async function loadEmployees() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/employees/')
    employees.value = response.data
  } catch (e) {
    error.value = 'Ошибка загрузки списка сотрудников'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    const response = await api.get('/departments/?flat=true')
    departments.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки подразделений:', e)
  }
}

async function loadSchedules() {
  try {
    const response = await api.get('/schedules/')
    schedules.value = response.data
  } catch (e) {
    console.error('Ошибка загрузки графиков:', e)
  }
}

function openAddDialog() {
  isEdit.value = false
  selectedEmployee.value = null
  tabNumber.value = ''
  fullName.value = ''
  departmentId.value = null
  scheduleId.value = null
  dialog.value = true
}

function openEditDialog(item) {
  isEdit.value = true
  selectedEmployee.value = item
  tabNumber.value = item.tab_number
  fullName.value = item.full_name
  departmentId.value = item.department_id
  scheduleId.value = item.schedule_id
  dialog.value = true
}

async function saveEmployee() {
  if (!tabNumber.value.trim() || !fullName.value.trim()) {
    error.value = 'Заполните обязательные поля'
    return
  }

  saving.value = true
  error.value = ''
  
  const payload = {
    tab_number: tabNumber.value,
    full_name: fullName.value,
    department_id: departmentId.value || null,
    schedule_id: scheduleId.value || null
  }
  
  try {
    if (isEdit.value) {
      await api.patch(`/employees/${selectedEmployee.value.id}`, payload)
    } else {
      await api.post('/employees/', payload)
    }
    dialog.value = false
    await loadEmployees()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка сохранения'
    console.error(e)
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  selectedEmployee.value = item
  deleteDialog.value = true
}

async function deleteEmployee() {
  deleting.value = true
  error.value = ''
  
  try {
    await api.delete(`/employees/${selectedEmployee.value.id}`)
    deleteDialog.value = false
    await loadEmployees()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка удаления'
    console.error(e)
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadEmployees()
  loadDepartments()
  loadSchedules()
})
</script>