<template>
  <v-container fill-height class="d-flex align-center justify-center" style="min-height: 80vh;">
    <v-card width="420" elevation="6" rounded="lg">
      <v-card-title class="text-center pt-6" style="color:#2d5a3d; font-weight:bold;">
        <v-icon size="42" color="#2d5a3d">mdi-fingerprint</v-icon>
        <div>Вход в систему</div>
      </v-card-title>
      <v-card-text>
        <v-form @submit.prevent="doLogin">
          <v-text-field
            v-model="username"
            label="Логин"
            prepend-inner-icon="mdi-account"
            variant="outlined"
            density="comfortable"
            autofocus
            class="mb-2"
          />
          <v-text-field
            v-model="password"
            label="Пароль"
            prepend-inner-icon="mdi-lock"
            :type="showPass ? 'text' : 'password'"
            :append-icon="showPass ? 'mdi-eye-off' : 'mdi-eye'"
            @click:append="showPass = !showPass"
            variant="outlined"
            density="comfortable"
          />
          <v-alert v-if="error" type="error" density="compact" class="mt-2" variant="tonal">
            {{ error }}
          </v-alert>
          <v-btn
            color="#2d5a3d"
            block
            class="mt-4"
            type="submit"
            :loading="loading"
            height="44"
          >
            Войти
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const showPass = ref(false)
const error = ref('')
const loading = ref(false)

async function doLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    router.push('/tabels')
  } catch (e) {
    error.value = e.response?.status === 401
      ? 'Неверный логин или пароль'
      : 'Ошибка сервера. Попробуйте ещё раз.'
  } finally {
    loading.value = false
  }
}
</script>
