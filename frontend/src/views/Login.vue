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
import { useRoute, useRouter } from 'vue-router'
import { auth } from '../auth'

const route = useRoute()
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

    // ✅ УМНЫЙ РЕДИРЕКТ: проверяем права ДО перехода, чтобы не зависнуть
    // на заблокированной роутером странице.
    // 1) Если пользователь пришёл сюда по редиректу с конкретной страницы
    //    (?redirect=...) и имеет на неё права — возвращаем его обратно.
    const requested = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (requested && !requested.startsWith('/login') && auth.hasPermission(requested)) {
      return router.push(requested)
    }
    // 2) Иначе — на первую доступную страницу из прав пользователя
    //    (учитывая админа и пользователей без permissions).
    const target = auth.firstAvailablePage()
    if (target) {
      return router.push(target)
    }
    // 3) Прав нет вообще — понятное сообщение вместо бесконечной загрузки.
    error.value = 'У вашей учетной записи нет доступа ни к одному разделу. Обратитесь к администратору.'
    auth.logout() // Сбрасываем сессию, чтобы не застрять на экране загрузки
  } catch (e) {
    console.error(e)
    error.value = e.response?.status === 401
      ? 'Неверный логин или пароль'
      : 'Ошибка сервера. Попробуйте ещё раз.'
  } finally {
    // ✅ ГАРАНТИРОВАННО останавливаем спиннер в любом случае
    loading.value = false
  }
}
</script>
