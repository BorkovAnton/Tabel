const path = require('path')

module.exports = {
  configureWebpack: {
    resolve: {
      alias: {
        // Явно фиксируем '@' → frontend/src, чтобы импорт иконок
        // '@/assets/icons/edit.png' работал гарантированно
        '@': path.resolve(__dirname, 'src'),
      },
    },
  },
  devServer: {
    host: '0.0.0.0',  // <-- ДОБАВИТЬ: слушать все сетевые интерфейсы
    port: 3000,        // <-- Ваш порт
    allowedHosts: 'all', // <-- Разрешить доступ с любых хостов
    client: {
      // «ResizeObserver loop completed with undelivered notifications» —
      // безвредное предупреждение браузеров (Vuetify/таблицы перерисовываются
      // быстрее, чем ResizeObserver успевает доставить уведомление).
      // Реальных ошибок оно не вызывает, поэтому скрываем его из error overlay,
      // остальные ошибки оставляем как есть.
      overlay: {
        errors: true,
        warnings: false,
        runtimeErrors: (error) => {
          if (error && /ResizeObserver loop/i.test(error.message || '')) return false
          return true
        },
      },
    },
  }
}