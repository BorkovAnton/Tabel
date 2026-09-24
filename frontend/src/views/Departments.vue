<template>
  <div style="padding: 20px;">
    <h1 style="font-size: 24px; font-weight: bold; margin-bottom: 20px;">Подразделения</h1>

    <button 
      @click="openAddDialog" 
      style="background: #1976d2; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 20px;"
    >
      + Добавить подразделение
    </button>

    <div v-if="loading" style="padding: 20px; text-align: center;">Загрузка...</div>
    
    <div v-else-if="departments.length === 0" style="padding: 20px; text-align: center; color: gray;">
      Нет подразделений
    </div>
    
    <div v-else style="border: 1px solid #e0e0e0; border-radius: 4px; padding: 10px;">
      <div v-for="dept in departments" :key="dept.id">
        <!-- Родительское подразделение -->
        <div 
          style="display: flex; align-items: center; padding: 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0;"
          @mouseenter="$event.currentTarget.style.backgroundColor = '#f5f5f5'"
          @mouseleave="$event.currentTarget.style.backgroundColor = 'transparent'"
        >
          <span 
            v-if="dept.children && dept.children.length > 0"
            @click.stop="toggleExpand(dept)"
            style="margin-right: 8px; cursor: pointer; width: 20px;"
          >
            {{ dept.expanded ? '▼' : '▶' }}
          </span>
          <span v-else style="width: 20px; display: inline-block;"></span>
          
          <span style="margin-right: 8px;">📁</span>
          
          <div style="flex-grow: 1;">
            <strong>{{ dept.name }}</strong>
            <span style="color: gray; margin-left: 8px;">({{ dept.employee_count }} сотр.)</span>
          </div>
          
          <button 
            @click.stop="openEditDialog(dept)"
            style="background: none; border: none; cursor: pointer; margin-right: 8px; font-size: 16px;"
            title="Редактировать"
          >
            ✏️
          </button>
          <button 
            @click.stop="confirmDelete(dept)"
            style="background: none; border: none; cursor: pointer; font-size: 16px;"
            title="Удалить"
          >
            🗑️
          </button>
        </div>
        
        <!-- Дочерние подразделения -->
        <div v-if="dept.expanded && dept.children && dept.children.length > 0" style="margin-left: 40px;">
          <div 
            v-for="child in dept.children" 
            :key="child.id"
            style="display: flex; align-items: center; padding: 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0;"
            @mouseenter="$event.currentTarget.style.backgroundColor = '#f5f5f5'"
            @mouseleave="$event.currentTarget.style.backgroundColor = 'transparent'"
          >
            <span 
              v-if="child.children && child.children.length > 0"
              @click.stop="toggleExpand(child)"
              style="margin-right: 8px; cursor: pointer; width: 20px;"
            >
              {{ child.expanded ? '▼' : '▶' }}
            </span>
            <span v-else style="width: 20px; display: inline-block;"></span>
            
            <span style="margin-right: 8px;">📁</span>
            
            <div style="flex-grow: 1;">
              <strong>{{ child.name }}</strong>
              <span style="color: gray; margin-left: 8px;">({{ child.employee_count }} сотр.)</span>
            </div>
            
            <button 
              @click.stop="openEditDialog(child)"
              style="background: none; border: none; cursor: pointer; margin-right: 8px; font-size: 16px;"
              title="Редактировать"
            >
              ✏️
            </button>
            <button 
              @click.stop="confirmDelete(child)"
              style="background: none; border: none; cursor: pointer; font-size: 16px;"
              title="Удалить"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Диалог добавления/редактирования -->
    <div v-if="dialog" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
      <div style="background: white; padding: 30px; border-radius: 8px; min-width: 400px;">
        <h2 style="margin-top: 0;">{{ isEdit ? 'Редактировать' : 'Добавить' }} подразделение</h2>
        
        <div style="margin-bottom: 20px;">
          <label style="display: block; margin-bottom: 5px;">Название:</label>
          <input 
            v-model="departmentName" 
            type="text" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
          />
        </div>
        
        <div style="margin-bottom: 20px;">
          <label style="display: block; margin-bottom: 5px;">Родительское подразделение:</label>
          <select 
            v-model="parentId" 
            style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
          >
            <option :value="null">-- Корневое подразделение --</option>
            <option v-for="dept in flatDepartments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
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
            @click="saveDepartment"
            style="padding: 8px 16px; border: none; background: #1976d2; color: white; border-radius: 4px; cursor: pointer;"
          >
            Сохранить
          </button>
        </div>
      </div>
    </div>

    <!-- Диалог подтверждения удаления -->
    <div v-if="deleteDialog" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
      <div style="background: white; padding: 30px; border-radius: 8px; min-width: 400px;">
        <h2 style="margin-top: 0;">Подтверждение удаления</h2>
        <p>Вы уверены, что хотите удалить подразделение "{{ selectedDepartment?.name }}"?</p>
        
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button 
            @click="deleteDialog = false"
            style="padding: 8px 16px; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;"
          >
            Отмена
          </button>
          <button 
            @click="deleteDepartment"
            style="padding: 8px 16px; border: none; background: #d32f2f; color: white; border-radius: 4px; cursor: pointer;"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const departments = ref([])
const flatDepartments = ref([])
const dialog = ref(false)
const deleteDialog = ref(false)
const isEdit = ref(false)
const selectedDepartment = ref(null)
const departmentName = ref('')
const parentId = ref(null)

function toggleExpand(dept) {
  dept.expanded = !dept.expanded
}

async function loadDepartments() {
  loading.value = true
  try {
    const [flatRes, treeRes] = await Promise.all([
      api.get('/departments/?flat=true'),
      api.get('/departments/tree')
    ])
    flatDepartments.value = flatRes.data
    
    const addExpanded = (items) => {
      items.forEach(item => {
        item.expanded = true
        if (item.children && item.children.length > 0) {
          addExpanded(item.children)
        }
      })
    }
    addExpanded(treeRes.data)
    departments.value = treeRes.data
  } catch (e) {
    console.error('Ошибка загрузки:', e)
    alert('Ошибка: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  isEdit.value = false
  selectedDepartment.value = null
  departmentName.value = ''
  parentId.value = null
  dialog.value = true
}

function openEditDialog(item) {
  isEdit.value = true
  selectedDepartment.value = item
  departmentName.value = item.name
  parentId.value = item.parent_id
  dialog.value = true
}

async function saveDepartment() {
  if (!departmentName.value.trim()) {
    alert('Введите название')
    return
  }

  saving.value = true
  try {
    const data = {
      name: departmentName.value,
      parent_id: parentId.value
    }

    if (isEdit.value) {
      await api.patch(`/departments/${selectedDepartment.value.id}`, data)
    } else {
      await api.post('/departments/', data)
    }
    dialog.value = false
    await loadDepartments()
  } catch (e) {
    alert(e.response?.data?.detail || 'Ошибка')
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  selectedDepartment.value = item
  deleteDialog.value = true
}

async function deleteDepartment() {
  deleting.value = true
  try {
    await api.delete(`/departments/${selectedDepartment.value.id}`)
    deleteDialog.value = false
    await loadDepartments()
  } catch (e) {
    alert(e.response?.data?.detail || 'Ошибка')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadDepartments()
})
</script>