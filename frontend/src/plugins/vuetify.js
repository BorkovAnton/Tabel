import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Реальная причина пустого пространства справа: Vuetify вычисляет
// max-width у v-container из breakpoints ТЕМы (по умолчанию xl = 1280px).
// Переопределяем breakpoint 'xl' на величину заведомо больше любого
// монитора — теперь даже контейнеры внутри страниц растягиваются
// на всю ширину экрана. Дополнительно все v-container по умолчанию
// fluid и без ограничения maxWidth.
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    themes: {
      light: {
        variables: {
          'breakpoints': {
            xs: 600,
            sm: 960,
            md: 1280,
            lg: 1920,
            xl: 100000, // ← ключевое: снимает ограничение 1280px
          },
        },
      },
    },
  },
  defaults: {
    VContainer: {
      fluid: true,
      maxWidth: false,
      class: 'full-width-container',
    },
  },
})

export default vuetify