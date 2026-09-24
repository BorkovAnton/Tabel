<template>
  <v-container>
    <v-row justify="center" class="mt-10">
      <v-col cols="12" md="8">
        <v-card elevation="4" class="pa-8 text-center">
          <v-icon size="80" color="primary" class="mb-4">mdi-clock-check-outline</v-icon>
          <h1 class="text-h4 mb-4">Система учёта рабочего времени</h1>
          <p class="text-subtitle-1 text-grey mb-8">
            Автоматизированный табельный учёт с интеграцией данных проходной
          </p>
          
          <v-row>
            <v-col cols="12" md="4">
              <v-card variant="outlined" class="pa-4">
                <v-icon size="48" color="blue" class="mb-2">mdi-account-group</v-icon>
                <h3 class="text-h6">Сотрудники</h3>
                <p class="text-body-2 text-grey">Управление персоналом</p>
                <v-btn color="primary" class="mt-4" to="/employees">
                  Перейти
                </v-btn>
              </v-card>
            </v-col>
            <v-col cols="12" md="4">
              <v-card variant="outlined" class="pa-4">
                <v-icon size="48" color="green" class="mb-2">mdi-file-upload</v-icon>
                <h3 class="text-h6">Импорт данных</h3>
                <p class="text-body-2 text-grey">Загрузка из Excel</p>
                <v-btn color="success" class="mt-4" to="/import">
                  Перейти
                </v-btn>
              </v-card>
            </v-col>
            <v-col cols="12" md="4">
              <v-card variant="outlined" class="pa-4">
                <v-icon size="48" color="orange" class="mb-2">mdi-calendar-month</v-icon>
                <h3 class="text-h6">Табель</h3>
                <p class="text-body-2 text-grey">Отчёты и расчёты</p>
                <v-btn color="warning" class="mt-4" to="/timesheet-report">
                  Перейти
                </v-btn>
              </v-card>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>