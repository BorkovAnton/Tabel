<template>
  <div>
    <h2 class="mb-4">Настройки</h2>

    <v-row>
      <v-col cols="12" md="6">
        <v-card class="pa-4" elevation="2">
          <v-card-title class="px-0 pt-0">Реквизиты предприятия</v-card-title>
          <v-card-subtitle class="px-0 pb-3">
            Используются в печатных формах табелей, отчётах Excel и шапках документов.
          </v-card-subtitle>

          <v-alert v-if="error" type="error" class="mb-4" density="compact" closable>{{ error }}</v-alert>
          <v-alert v-if="saved" type="success" class="mb-4" density="compact" closable>
            Настройки сохранены
          </v-alert>

          <v-form @submit.prevent="save">
            <v-text-field
              v-model="form.company_name"
              label="Название предприятия"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              :loading="loading"
              :disabled="!auth.isAdmin"
              :rules="[v => !!String(v || '').trim() || 'Обязательное поле']"
              persistent-hint
              hint="Например: ООО «СтройИнвест»"
            />

            <v-text-field
              v-model="form.director_position"
              label="Должность руководителя"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              :disabled="!auth.isAdmin"
              hint="Например: Генеральный директор"
            />

            <v-text-field
              v-model="form.director_name"
              label="ФИО руководителя"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              :rules="[v => !!String(v || '').trim() || 'Обязательное поле']"
              :disabled="!auth.isAdmin"
              hint="Например: Иванов Иван Иванович"
            />

            <div class="mt-4">
              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-content-save"
                :loading="saving"
                :disabled="!auth.isAdmin || loading"
                @click="save"
              >
                Сохранить
              </v-btn>
              <v-btn
                v-if="!saving && isDirty"
                variant="text"
                class="ml-2"
                prepend-icon="mdi-restore"
                @click="load"
              >
                Сбросить изменения
              </v-btn>
            </div>

            <v-alert v-if="!auth.isAdmin" type="info" class="mt-4" density="compact">
              Просмотр настроек доступен всем, изменять их может только Администратор.
            </v-alert>
          </v-form>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card class="pa-4" elevation="2">
          <v-card-title class="px-0 pt-0">Предпросмотр в документах</v-card-title>
          <v-card-subtitle class="px-0 pb-3">
            Так данные будут выглядеть в шапке табеля / отчёта:
          </v-card-subtitle>

          <div class="doc-preview mt-2">
            <div class="text-h6 text-center">{{ form.company_name || 'Название предприятия' }}</div>
            <div class="text-center mt-4">{{ form.director_position || 'Генеральный директор' }}</div>
            <div class="text-center font-weight-medium">{{ form.director_name || 'ФИО руководителя' }}</div>
            <div class="text-caption d-block text-center mt-4 grey--text">
              «Утверждаю» — подпись руководителя на печатной форме табеля
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import api from '../api'
import { auth } from '../auth'

const loading = ref(false)
const saving = ref(false)
const saved = ref(false)
const error = ref('')
const original = ref(null)

const form = reactive({
  company_name: '',
  director_position: 'Генеральный директор',
  director_name: '',
})

const isDirty = computed(() => {
  if (!original.value) return false
  return (
    form.company_name !== original.value.company_name ||
    form.director_position !== original.value.director_position ||
    form.director_name !== original.value.director_name
  )
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/company-settings/')
    form.company_name = data.company_name || ''
    form.director_position = data.director_position || 'Генеральный директор'
    form.director_name = data.director_name || ''
    original.value = { ...data }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось загрузить настройки'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!String(form.company_name).trim()) {
    error.value = 'Заполните название предприятия'
    return
  }
  if (!String(form.director_name).trim()) {
    error.value = 'Заполните ФИО руководителя'
    return
  }
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    const { data } = await api.put('/company-settings/', {
      company_name: form.company_name.trim(),
      director_position: (form.director_position || 'Генеральный директор').trim(),
      director_name: form.director_name.trim(),
    })
    form.company_name = data.company_name
    form.director_position = data.director_position
    form.director_name = data.director_name
    original.value = { ...data }
    saved.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось сохранить настройки'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.doc-preview {
  border: 1px solid #c8e6c9;
  border-radius: 8px;
  background: #f1f8e9;
  padding: 24px;
  min-height: 220px;
}
</style>
