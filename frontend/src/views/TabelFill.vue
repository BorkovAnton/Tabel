<template>
  <div v-if="tabel">
    <div class="d-flex align-center mb-3 flex-wrap" style="gap: 8px;">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="'/tabels'" color="#2d5a3d">К табелям</v-btn>
      <h2 class="text-h5" style="font-weight:bold;">
        Табель: {{ monthNames[tabel.month - 1] }} {{ tabel.year }}
        <span v-if="tabel.department_name">— {{ tabel.department_name }}</span>
      </h2>
      <v-spacer />

      <v-btn variant="tonal" color="#2d5a3d" prepend-icon="mdi-book-outline" @click="codesDialog = true">
        Коды часов
      </v-btn>
      <v-btn variant="outlined" color="primary" prepend-icon="mdi-calendar-clock" :disabled="!tabel?.entries?.length" @click="openFillByScheduleDialog">
        Заполнить по графику
      </v-btn>
      <!-- ЗАПОЛНИТЬ ЧИСЛО: выбранный код в конкретную дату для всех сотрудников -->
      <v-btn variant="outlined" color="success" prepend-icon="mdi-calendar-check"
             :disabled="!tabel?.entries?.length" @click="openFillDayDialog">
        Заполнить число
      </v-btn>
      <!-- ЗАПОЛНИТЬ СОТРУДНИКА: выбранный код на весь месяц для выделенного сотрудника -->
      <v-btn variant="outlined" color="success" prepend-icon="mdi-account-edit"
             :disabled="selectedRow === null" @click="openFillEmployeeDialog">
        Заполнить сотрудника
      </v-btn>
      <v-btn color="green darken-1" prepend-icon="mdi-content-save" :loading="saving" @click="save(true)">
        Сохранить
      </v-btn>
    </div>

    <v-alert v-if="message" :type="messageType" closable density="compact" class="mb-3" @click:close="message=''">
      {{ message }}
    </v-alert>

    <div class="d-flex align-center flex-wrap mb-2" style="gap: 14px; font-size: 13px;">
      <span><span class="legend-box legend-weekend"></span> Выходной день</span>
      <span><span class="legend-box legend-holiday"></span> ★ Праздничный (нерабочий) день</span>
      <span v-if="calendarNotLoaded" class="text-caption text-grey-darken-1">
        Производственный календарь на {{ tabel.year }} год не загружен — показаны только выходные по пятидневке.
        Загрузите календарь на вкладке «Импорт».
      </span>
    </div>

    <div class="tabel-scroll" style="border:1px solid #c8e6c9; border-radius:8px; background:white;">
      <table class="tabel-table" v-if="tabel.entries.length">
        <thead>
          <!-- ПЕРВЫЙ УРОВЕНЬ ШАПКИ (закреплён сверху при прокрутке) -->
          <tr>
            <th class="col-no sticky-top sticky-left-1" rowspan="2">№<br>п/п</th>
            <th class="col-fio sticky-top sticky-left-2" rowspan="2">Ф.И.О.</th>
            <th class="col-days-header sticky-top" :colspan="tabel.days_in_month">Дни недели</th>
            <th v-for="col in summaryColumns" :key="col.key" class="col-summary-header sticky-top" rowspan="2"
                :title="col.label">
              {{ col.label }}
            </th>
            <th class="col-del sticky-top sticky-right" rowspan="2"></th>
          </tr>
          <!-- ВТОРОЙ УРОВЕНЬ ШАПКИ: дни недели + числа (тоже закреплён) -->
          <tr>
            <th v-for="d in tabel.days_in_month" :key="d" class="col-day-header sticky-top-l2"
                :class="{ 'day-weekend-header': isWeekend(d), 'day-holiday-header': isHoliday(d) }"
                :title="holidayName(d)">
              <div class="day-name">{{ getDayOfWeek(d) }}</div>
              <div class="day-number">{{ d }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in tabel.entries" :key="row.employee_id"
              :class="{ 'row-selected': selectedRow === idx }" @click="selectRow(idx)">
            <td class="col-no sticky-left-1"><div class="sticky-fill">{{ idx + 1 }}</div></td>
            <td class="col-fio sticky-left-2" :title="row.full_name"><div class="sticky-fill" style="flex-direction: column; align-items: flex-start;">
              {{ row.full_name }}<br /><small class="text-grey">{{ row.tab_number }}</small>
            </div></td>
            <td v-for="d in tabel.days_in_month" :key="d" class="cell-day"
                :class="{ 'cell-weekend': isWeekend(d), 'cell-holiday': isHoliday(d) }">
              <div class="cell-wrap" :class="{ 'is-open': openCell === row.employee_id + '_' + d }">
                <v-tooltip location="bottom" :max-width="220" :disabled="!row.days[d]">
                  <template #activator="{ props: tooltipProps }">
                    <input
                      class="cell-input cell-tip-area"
                      :class="{ 'is-code': isCodeText(row.days[d]), 'is-error-cell': hasError(row.employee_id, d), 'is-overtime-cell': isOvertimeCell(row, row.days[d], d) }"
                      :value="row.days[d] || ''"
                      readonly
                      tabindex="-1"
                      v-bind="tooltipProps"
                      @click.stop="openCellPicker(row.employee_id, d, $event)"
                    />
                  </template>
                  <!-- Подсказка с деталями ячейки: код из справочника / числовые часы -->
                  <div v-if="cellTipData(row.days[d], row, d)" class="day-tooltip">
                    <div class="font-weight-bold mb-1">{{ tooltipDateLabel(d) }}</div>
                    <template v-if="cellTipData(row.days[d], row, d).kind === 'code'">
                      <div><v-icon size="x-small" icon="mdi-tag-text-outline" class="mr-1" />Код: {{ cellTipData(row.days[d], row, d).code }}</div>
                      <div><v-icon size="x-small" icon="mdi-information-outline" class="mr-1" />{{ cellTipData(row.days[d], row, d).name }}</div>
                      <v-divider class="tooltip-divider my-1"></v-divider>
                      <div><v-icon size="x-small" icon="mdi-weather-sunny" class="mr-1" />День: {{ fmtNum(cellTipData(row.days[d], row, d).day) }}</div>
                      <div><v-icon size="x-small" icon="mdi-weather-night" class="mr-1" />Ночь: {{ fmtNum(cellTipData(row.days[d], row, d).night) }}</div>
                      <div class="font-weight-bold"><v-icon size="x-small" icon="mdi-check-circle-outline" class="mr-1" />Итого часов: {{ fmtNum(cellTipData(row.days[d], row, d).total) }}</div>
                      <div v-if="cellTipData(row.days[d], row, d).schedNote" class="text-caption text-grey-darken-1">
                        <v-icon size="x-small" icon="mdi-information-outline" class="mr-1" />{{ cellTipData(row.days[d], row, d).schedNote }}
                      </div>
                      <div v-if="cellTipData(row.days[d], row, d).ot > 0" class="text-warning">
                        <v-icon size="x-small" icon="mdi-alert-outline" class="mr-1" />Сверхурочно: {{ fmtNum(cellTipData(row.days[d], row, d).ot) }} (норма по графику {{ fmtNum(getDayNorm(row, d)) }})
                      </div>
                    </template>
                    <template v-else>
                      <div><v-icon size="x-small" icon="mdi-clock-outline" class="mr-1" />Введено: {{ fmtNum(cellTipData(row.days[d], row, d).hours) }} ч.</div>
                      <div><v-icon size="x-small" icon="mdi-target" class="mr-1" />Норма по графику: {{ fmtNum(cellTipData(row.days[d], row, d).norm) }} ч.</div>
                      <v-divider class="tooltip-divider my-1"></v-divider>
                      <div><v-icon size="x-small" icon="mdi-briefclockcase-outline" class="mr-1" />Обычные: {{ fmtNum(cellTipData(row.days[d], row, d).regular) }} ч.</div>
                      <div v-if="cellTipData(row.days[d], row, d).ot > 0" class="text-warning font-weight-bold">
                        <v-icon size="x-small" icon="mdi-alert-outline" class="mr-1" />Сверхурочные: {{ fmtNum(cellTipData(row.days[d], row, d).ot) }} ч.
                      </div>
                    </template>
                  </div>
                  <!-- Пустая ячейка: tooltip отключён (:disabled), текст доступен через cellTipText -->
                  <div v-else class="day-tooltip">
                    <div class="font-weight-bold mb-1">{{ tooltipDateLabel(d) }}</div>
                    <div class="text-caption">{{ cellTipText(null) }}</div>
                  </div>
                </v-tooltip>
                <v-menu
                  :model-value="openCell === row.employee_id + '_' + d"
                  :positioned="true"
                  :style="{ left: menuX + 'px', top: menuY + 'px' }"
                  :scrim="false"
                  :hide-scroll="false"
                  :min-width="260"
                  content-class="cell-menu"
                  max-height="320"
                  @update:model-value="(v) => { if (!v) openCell = null }"
                >
                  <div style="width: 300px;">
                    <v-text-field
                      ref="cellSearchRef"
                      v-model="cellQuery"
                      density="compact"
                      variant="solo-filled"
                      flat-end
                      hide-details
                      clearable
                      placeholder="Поиск (напр. 8)"
                      prepend-inner-icon="mdi-magnify"
                      autofocus
                      class="pa-1"
                    />
                    <v-list density="compact" max-height="260" class="overflow-y-auto">
                      <v-list-item
                        value="__clear__"
                        class="code-menu-clear"
                        prepend-icon="mdi-close-circle-outline"
                        title="Очистить ячейку"
                        @click.stop="clearCell(row.employee_id, d)"
                      />
                      <v-divider />
                      <v-list-item
                        v-for="it in filteredCellItems"
                        :key="it.value"
                        :title="it.title"
                        prepend-icon="mdi-check"
                        @click.stop="pickCellValue(row.employee_id, d, it.value)"
                      />
                      <v-list-item v-if="!filteredCellItems.length" title="Ничего не найдено" disabled />
                    </v-list>
                  </div>
                </v-menu>
              </div>
            </td>
            <!-- ЗНАЧЕНИЯ ИТОГОВЫХ КОЛОНОК -->
            <td v-for="col in summaryColumns" :key="col.key" class="col-summary-cell text-center">
              <!-- Ручные колонки КДУ: редактируемый input (0..5, шаг 0.01) -->
              <input
                v-if="col.unit === 'manual'"
                type="number"
                class="kdu-input"
                min="0" max="5" step="0.01"
                :value="row[col.key] ?? ''"
                @input="onKduInput(row, col.key, $event)"
                @blur="onKduBlur(row, col.key)"
                @keyup.enter="onKduBlur(row, col.key); $event.target.blur()"
                @click.stop
              />
              <template v-else>{{ calculateSummary(row)[col.key] || 0 }}</template>
            </td>
            <td class="col-del sticky-right">
              <div class="sticky-fill d-flex align-center justify-end" style="gap: 6px; flex-wrap: wrap;">
                <span class="code-chips" v-if="codesForRow(row).length">
                  <v-chip v-for="c in codesForRow(row)" :key="c.code" size="x-small"
                          variant="tonal" color="#2d5a3d" style="margin:1px;">{{ c.code }}</v-chip>
                </span>
                <a href="#" class="text-red text-caption" style="white-space:nowrap;"
                   @click.prevent.stop="removeEmployee(row)">Удалить</a>
              </div>
            </td>
          </tr>

          <tr class="add-row">
            <td class="sticky-left-1"><div class="sticky-fill"></div></td>
            <td class="add-cell sticky-left-2"><div class="sticky-fill" style="justify-content: flex-start; min-height: 48px;">
              <div class="d-flex align-center" style="gap: 6px;">
                <v-autocomplete
                  v-model="selectedEmployee"
                  :items="employeeOptions"
                  item-title="label"
                  item-value="id"
                  :menu-icon="null"
                  label="Добавить сотрудника (поиск по ФИО, таб. номеру, подразделению)"
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  variant="outlined"
                  clearable
                  hide-details
                  auto-select-first
                  no-filter
                  :filter="filterEmployees"
                  no-data-text="Ничего не найдено"
                  style="min-width: 320px; max-width: 420px;"
                  @update:model-value="onEmployeePicked"
                  @update:search="onEmpSearch"
                >
                  <template #item="{ props, item }">
                    <!-- ФИО рендерим явно: Vuetify с auto-select-first закрашивал
                         подсветку (оранжевый) ПОВЕРХ текста стандартного title-слоя,
                         из-за чего надпись сливалась с выделением. span.emp-search-title
                         лежит в слое выше .v-list-item__overlay (z-index) и всегда
                         остаётся тёмным и читаемым на любом фоне. -->
                    <v-list-item v-bind="props">
                      <template #prepend>
                        <span class="emp-search-title">{{ item.raw.label }}</span>
                      </template>
                      <template #append>
                        <span v-if="item.raw.tab_number" class="emp-search-subtitle">Таб. {{ item.raw.tab_number }}</span>
                      </template>
                    </v-list-item>
                  </template>
                </v-autocomplete>
                <span v-if="selectedEmployee" class="text-caption text-grey">— строка появится здесь</span>
              </div>
            </div></td>
            <td :colspan="tabel.days_in_month + summaryColumns.length + 1"></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="pa-4">
        <div class="d-flex align-center mb-4" style="gap: 6px;">
          <v-autocomplete
            v-model="selectedEmployee"
            :items="employeeOptions"
            item-title="label"
            item-value="id"
            :menu-icon="null"
            label="Добавить сотрудника (поиск по ФИО, таб. номеру, подразделению)"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            clearable
            hide-details
            auto-select-first
            no-filter
            :filter="filterEmployees"
            no-data-text="Ничего не найдено"
            style="min-width: 320px; max-width: 420px;"
            @update:model-value="onEmployeePicked"
            @update:search="onEmpSearch"
          >
            <template #item="{ props, item }">
              <!-- Тот же приём, что и в строке добавления сотрудника: ФИО рендерится
                   явным span.emp-search-title поверх слоя подсветки, чтобы текст не
                   сливался с оранжевым выделением активного элемента. -->
              <v-list-item v-bind="props">
                <template #prepend>
                  <span class="emp-search-title">{{ item.raw.label }}</span>
                </template>
                <template #append>
                  <span v-if="item.raw.tab_number" class="emp-search-subtitle">Таб. {{ item.raw.tab_number }}</span>
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>
          <span class="text-caption text-grey">— первый сотрудник появится здесь</span>
        </div>
      </div>
    </div>

    <!-- Справочник «Коды часов» -->
    <v-dialog v-model="codesDialog" max-width="900">
      <v-card title="Справочник «Коды часов»">
        <v-card-text>
          <v-table density="compact" hover>
            <thead>
              <tr>
                <th style="width: 80px;">Код</th>
                <th>Наименование</th>
                <th style="width: 80px;">Часов день</th>
                <th style="width: 90px;">Часов ночь</th>
                <th style="width: 110px;" title="Часы берутся из нормы графика работы на конкретный день">По графику</th>
                <th style="width: 110px;" title="Фиксированные часы в выходные/праздники (норма 0), например 8 для командировки «К»">Часы в выходной</th>
                <th style="min-width: 250px; max-width: 400px;">Направления</th>
                <th v-if="auth.isAdmin" style="width: 100px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in timeCodes" :key="c.id" class="code-row">
                <td><b>{{ c.code }}</b></td>
                <td>{{ c.name }}</td>
                <td class="text-center">{{ c.hours_day }}</td>
                <td class="text-center">{{ c.hours_night }}</td>
                <td class="text-center">
                  <v-icon v-if="c.use_schedule_hours" size="small" color="#e65100">mdi-check-circle</v-icon>
                  <span v-else class="text-grey text-caption">—</span>
                </td>
                <td class="text-center">
                  <span v-if="c.weekend_hours != null && c.weekend_hours !== ''">{{ Number(c.weekend_hours) || 0 }}</span>
                  <span v-else class="text-grey text-caption">—</span>
                </td>
                
                <td style="white-space: normal !important; vertical-align: middle;">
                  <div class="d-flex flex-wrap" style="gap: 4px;">
                    <v-chip v-for="dest in (c.destinations || [])" :key="dest" size="x-small" variant="tonal" color="#2d5a3d">
                      {{ destinationOptions.find(col => col.value === dest)?.title || dest }}
                    </v-chip>
                    <span v-if="!c.destinations || c.destinations.length === 0" class="text-grey text-caption">Не указано</span>
                  </div>
                </td>
                
                <td v-if="auth.isAdmin" class="text-center">
                  <v-btn size="x-small" icon="mdi-pencil" color="blue" variant="text" @click="editCode(c)" class="mr-1" />
                  <v-btn size="x-small" icon="mdi-delete" color="red" variant="text" @click="deleteCode(c)" />
                </td>
              </tr>
            </tbody>
          </v-table>
          
          <template v-if="auth.isAdmin">
            <v-divider class="my-4" />
            <div class="text-h6 mb-3">
              {{ isEditing ? 'Редактирование кода' : 'Добавление нового кода' }}
              <span v-if="isEditing" class="text-caption text-grey ml-2">({{ editingCode?.code }})</span>
            </div>
            
            <v-form @submit.prevent="saveCode" class="d-flex flex-wrap" style="gap:8px; align-items: flex-start;">
              <v-text-field 
                v-model="newCode.code" 
                :label="isEditing ? 'Код (нельзя изменить)' : 'Код'" 
                :readonly="isEditing"
                density="compact" 
                variant="outlined" 
                style="max-width:100px;" 
                hide-details 
              />
              <v-text-field 
                v-model="newCode.name" 
                label="Наименование" 
                density="compact" 
                variant="outlined" 
                style="flex:1; min-width: 150px;" 
                hide-details 
              />
              <v-text-field 
                v-model.number="newCode.hours_day" 
                label="День" 
                type="number" 
                step="0.01" 
                density="compact" 
                variant="outlined" 
                style="max-width:80px;" 
                hide-details 
              />
              <v-text-field 
                v-model.number="newCode.hours_night" 
                label="Ночь" 
                type="number" 
                step="0.01" 
                density="compact" 
                variant="outlined" 
                style="max-width:80px;" 
                hide-details 
              />
              
              <v-checkbox
                v-model="newCode.use_schedule_hours"
                label="Время по графику"
                density="compact"
                hide-details
                class="align-self-center mt-0"
                style="max-width: 190px;"
                title="Часы берутся из нормы графика работы на конкретный день (пн — 8.25ч, пт — 7ч и т.п.), например для командировок"
              />

              <v-text-field
                v-model.number="newCode.weekend_hours"
                label="Часы в выходной"
                type="number"
                step="0.01"
                min="0"
                density="compact"
                variant="outlined"
                style="max-width:130px;"
                hide-details
                :disabled="!newCode.use_schedule_hours"
                title="Фиксированные часы для выходных/праздников (норма графика = 0). Например, 8 для «К»: в будни — по графику, в выходной — 8 ч. Пусто — как раньше (0 ч)."
              />

              <v-select
                v-model="newCode.destinations"
                :items="destinationOptions"
                item-title="title"
                item-value="value"
                label="Куда попадет"
                density="compact"
                variant="outlined"
                multiple
                chips
                closable-chips
                style="min-width: 250px; flex: 2;"
                hide-details
              />
              
              <v-btn color="#2d5a3d" type="submit" prepend-icon="mdi-content-save" class="align-self-end" style="height: 40px;">
                {{ isEditing ? 'Сохранить' : 'Добавить' }}
              </v-btn>
              
              <v-btn v-if="isEditing" variant="outlined" color="grey" @click="cancelEdit" class="align-self-end" style="height: 40px;">
                Отмена
              </v-btn>
            </v-form>
            
            <div v-if="codeError" class="text-red mt-2">{{ codeError }}</div>
          </template>
          <div v-else class="text-caption text-grey mt-2">
            Изменять справочник может только Администратор.
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="codesDialog = false">Закрыть</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог «Заполнить по графику»: автораспределение выбранных кодов по рабочим дням -->
    <v-dialog v-model="fillDialog" max-width="520">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-calendar-clock" color="primary" class="mr-2" />
          Заполнить по графику
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-3 text-grey-darken-2">
            Каждый день месяца будет заполнен кодом из поля
            <b>«Код для автозаполнения»</b> графика работы конкретного сотрудника
            (настраивается в разделе «Графики работы»). Например, для Пн–Пт указан
            код «8ч15м», для Сб–Вс — «В»: эти же коды подставятся в соответствующие
            дни. Выходные и праздники (норма 0 ч) также заполняются, если для них
            в графике задан код (например «В»). Если для дня недели код в графике
            не указан — день пропускается. Изменения не сохранятся, пока вы не
            нажмёте «Сохранить» — заполнение можно скорректировать вручную.
          </div>

          <v-alert v-if="fillMissingCodes.length" type="warning" density="compact" variant="tonal" class="mb-3">
            В графиках сотрудников не указан «Код для автозаполнения» для норм:
            {{ fillMissingCodes.join(', ') }} ч. Эти дни будут пропущены — укажите
            коды в разделе «Графики работы».
          </v-alert>

          <v-checkbox
            v-model="overwriteExisting"
            label="Перезаписать существующие значения"
            density="compact"
            hide-details
            class="mt-0"
          />
          <div v-if="!overwriteExisting" class="text-caption text-grey ml-1 mb-2">
            Пустые ячейки будут заполнены, уже заполненные останутся без изменений.
          </div>

          <v-alert v-if="fillPreview.workDaysTotal === 0" type="info" density="compact" variant="tonal" class="mt-2">
            Не найдено ни одного дня с заполненным «Кодом для автозаполнения» в
            графиках работы сотрудников. Укажите коды (например «8ч15м» для рабочих
            дней и «В» для выходных) в разделе «Графики работы».
          </v-alert>
          <v-alert v-else-if="fillPreview.toFill === 0" type="warning" density="compact" variant="tonal" class="mt-2">
            Заполнять нечего: включите «Перезаписать существующие» или укажите
            «Код для автозаполнения» в графиках работы.
          </v-alert>
          <div v-else class="text-body-2 mt-2">
            Будет заполнено ячеек:
            <b class="text-primary">{{ fillPreview.toFill }}</b>
            <span class="text-caption text-grey">
              (рабочих дней: {{ fillPreview.workDaysTotal }},
              без кода в графике: {{ fillPreview.skippedNoCode }},
              пропущено заполненных: {{ fillPreview.skippedFilled }})
            </span>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="fillDialog = false">Отмена</v-btn>
          <v-btn color="primary" prepend-icon="mdi-calendar-check" :disabled="fillPreview.toFill === 0" @click="applyFillBySchedule">
            Заполнить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог «Заполнить число»: выбранный код в конкретную дату для ВСЕХ сотрудников -->
    <v-dialog v-model="fillDayDialog" max-width="520">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-calendar-check" color="success" class="mr-2" />
          Заполнить число
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-3 text-grey-darken-2">
            Заполнение конкретной даты для <b>всех сотрудников</b> табеля.
            По умолчанию значение берётся <b>из графика работы каждого
            сотрудника</b>: код из поля «Код для автозаполнения» (например
            «8ч15м» в будни, «В» в выходные). Если снять галочку — во все ячейки
            этой даты будет поставлен выбранный вручную код (например «К» —
            командировка на 15 сентября). Изменения не сохранятся, пока вы не
            нажмёте «Сохранить» — заполнение можно скорректировать вручную.
          </div>

          <v-select
            v-model="fillDayDate"
            :items="dayItems"
            item-title="title"
            item-value="value"
            label="Дата (число месяца)"
            density="compact"
            hide-details="auto"
            class="mb-3"
          />

          <v-checkbox
            v-model="fillByScheduleDay"
            label="Заполнять по графику сотрудника (код из графика / нормы дня)"
            density="compact"
            hide-details
            class="mt-0 mb-1"
          />

          <template v-if="!fillByScheduleDay">
            <v-combobox
              v-model="fillDayCode"
              :items="codeListItems"
              label="Код заполнения"
              density="compact"
              hide-details="auto"
              class="mb-1"
            />
            <div class="text-caption text-grey mb-2">
              Можно выбрать код из справочника или ввести значение вручную
              (например «8ч15м», «10»).
            </div>
            <div v-if="fillDayCode && !isValidValue(fillDayCode)" class="text-error text-caption mb-2">
              Неизвестный код или неверное значение — выберите код из справочника
              или введите часы (например «8ч15м» или «10»).
            </div>
          </template>
          <div v-else class="text-caption text-grey mb-2">
            Для каждого сотрудника подставляется код из его графика:
            «Код для автозаполнения» этого дня недели; если он не задан в
            будний день — ближайший код справочника по норме часов дня.
            Дни без кода в графике пропускаются.
          </div>

          <v-checkbox
            v-model="overwriteExistingDay"
            label="Перезаписать существующие значения"
            density="compact"
            hide-details
            class="mt-0"
          />

          <v-alert v-if="fillDayPreview.total === 0" type="info" density="compact" variant="tonal" class="mt-2">
            В табеле нет сотрудников — заполнять нечего.
          </v-alert>
          <v-alert v-else-if="fillDayPreview.toFill === 0" type="warning" density="compact" variant="tonal" class="mt-2">
            <template v-if="fillByScheduleDay">
              Ни для одного сотрудника в графике нет кода автозаполнения на эту
              дату (либо все ячейки уже заполнены — включите перезапись).
            </template>
            <template v-else>
              Все ячейки за выбранную дату уже заполнены. Включите
              «Перезаписать существующие значения», чтобы обновить их.
            </template>
          </v-alert>
          <div v-else class="text-body-2 mt-2">
            Будет заполнено ячеек:
            <b class="text-primary">{{ fillDayPreview.toFill }}</b>
            <span class="text-caption text-grey">
              (сотрудников: {{ fillDayPreview.total }},
              пропущено заполненных: {{ fillDayPreview.skippedFilled }},
              без кода в графике: {{ fillDayPreview.skippedNoCode }})
            </span>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="fillDayDialog = false">Отмена</v-btn>
          <v-btn color="success" prepend-icon="mdi-calendar-check"
                 :disabled="fillDayPreview.toFill === 0 || (!fillByScheduleDay && (!fillDayCode || !isValidValue(fillDayCode)))"
                 @click="applyFillDay">
            Заполнить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Диалог «Заполнить сотрудника»: выбранный код на весь месяц для выделенного сотрудника -->
    <v-dialog v-model="fillEmpDialog" max-width="520">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-account-edit" color="success" class="mr-2" />
          Заполнить сотрудника
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-3 text-grey-darken-2">
            Заполнение <b>всего месяца</b> для выделенного сотрудника. По
            умолчанию значения берутся <b>из его индивидуального графика</b>:
            код из поля «Код для автозаполнения» (например «8ч15м» в будни,
            «В» в выходные). Если снять галочку — выбранный вручную код будет
            поставлен во все дни месяца. Кликните по строке табеля, чтобы
            выделить сотрудника. Изменения не сохранятся, пока вы не нажмёте
            «Сохранить» — заполнение можно скорректировать вручную.
          </div>

          <v-alert v-if="selectedRowEntry" type="info" density="compact" variant="tonal" class="mb-3">
            Выделен сотрудник: <b>{{ selectedRowEntry.full_name }}</b>
            <span v-if="selectedRowEntry.tab_number"> (Таб. {{ selectedRowEntry.tab_number }})</span>
          </v-alert>

          <v-checkbox
            v-model="fillByScheduleEmp"
            label="Заполнять по графику сотрудника (код из графика / нормы дня)"
            density="compact"
            hide-details
            class="mt-0 mb-1"
          />

          <template v-if="!fillByScheduleEmp">
            <v-combobox
              v-model="fillEmpCode"
              :items="codeListItems"
              label="Код заполнения"
              density="compact"
              hide-details="auto"
              class="mb-1"
            />
            <div class="text-caption text-grey mb-2">
              Можно выбрать код из справочника или ввести значение вручную
              (например «8ч15м», «10»).
            </div>
            <div v-if="fillEmpCode && !isValidValue(fillEmpCode)" class="text-error text-caption mb-2">
              Неизвестный код или неверное значение — выберите код из справочника
              или введите часы (например «8ч15м» или «10»).
            </div>
          </template>
          <div v-else class="text-caption text-grey mb-2">
            Для каждого дня подставляется код из графика сотрудника:
            «Код для автозаполнения» этого дня недели; если он не задан в
            будний день — ближайший код справочника по норме часов дня.
            Дни без кода в графике пропускаются.
          </div>

          <v-checkbox
            v-model="overwriteExistingEmp"
            label="Перезаписать существующие значения"
            density="compact"
            hide-details
            class="mt-0"
          />

          <v-alert v-if="!selectedRowEntry" type="warning" density="compact" variant="tonal" class="mt-2">
            Сотрудник не выделен — кликните по строке в табеле.
          </v-alert>
          <v-alert v-else-if="fillEmpPreview.toFill === 0" type="warning" density="compact" variant="tonal" class="mt-2">
            <template v-if="fillByScheduleEmp">
              В графике этого сотрудника нет кодов автозаполнения на дни месяца
              (либо все дни уже заполнены — включите перезапись).
            </template>
            <template v-else>
              Все дни этого сотрудника уже заполнены. Включите
              «Перезаписать существующие значения», чтобы обновить их.
            </template>
          </v-alert>
          <div v-else-if="selectedRowEntry" class="text-body-2 mt-2">
            Будет заполнено ячеек:
            <b class="text-primary">{{ fillEmpPreview.toFill }}</b>
            <span class="text-caption text-grey">
              (дней в месяце: {{ fillEmpPreview.daysTotal }},
              пропущено заполненных: {{ fillEmpPreview.skippedFilled }},
              без кода в графике: {{ fillEmpPreview.skippedNoCode }})
            </span>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="fillEmpDialog = false">Отмена</v-btn>
          <v-btn color="success" prepend-icon="mdi-account-check"
                 :disabled="!selectedRowEntry || fillEmpPreview.toFill === 0 || (!fillByScheduleEmp && (!fillEmpCode || !isValidValue(fillEmpCode)))"
                 @click="applyFillEmployee">
            Заполнить
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <v-progress-circular v-else indeterminate color="#2d5a3d" />
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { auth } from '../auth'

const route = useRoute()
const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const dayOfWeekNames = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

const tabel = ref(null)
const timeCodes = ref([])
const dirty = ref({})
const dirtyKdu = ref({})   // изменённые ручные значения КДУ: key = `${employee_id}_${field}`
const cellErrors = ref({})
const message = ref('')
const messageType = ref('success')
const saving = ref(false)

const codesDialog = ref(false)
const newCode = ref({ code: '', name: '', hours_day: 0, hours_night: 0, use_schedule_hours: false, weekend_hours: null, destinations: [] })
const codeError = ref('')
const isEditing = ref(false)
const editingCode = ref(null)

// ─── «Заполнить по графику» ────────────────────────────────────────────────
// Диалог автораспределения кодов по рабочим дням месяца ПО ИНДИВИДУАЛЬНОМУ
// графику каждого сотрудника: код берётся напрямую из поля «Код для
// автозаполнения» (auto_fill_code) дня недели графика (row.day_auto_codes[d]);
// рабочий день — норма > 0 (day_norms[d]) и заданный код в графике.
const fillDialog = ref(false)
const overwriteExisting = ref(true)  // перезаписывать уже заполненные ячейки или нет

// ─── «Заполнить число» / «Заполнить сотрудника» ────────────────────────────
// fillDayDialog  — выбранный код ставится в одну дату всем сотрудникам табеля.
// fillEmpDialog  — выбранный код ставится на весь месяц выделенному сотруднику.
// selectedRow    — индекс выделенной строки табеля (null — никто не выделен).
const fillDayDialog = ref(false)
const fillEmpDialog = ref(false)
const fillDayDate = ref(null)        // число месяца (1..days_in_month)
const fillDayCode = ref('')          // код/значение для заполнения даты
const fillEmpCode = ref('')          // код/значение для заполнения сотрудника
const overwriteExistingDay = ref(true)
const overwriteExistingEmp = ref(true)
// По умолчанию заполнение идёт ПО ГРАФИКУ сотрудника (auto_fill_code / норма);
// если снять галочку — ставится выбранный вручную код во все ячейки.
const fillByScheduleDay = ref(true)
const fillByScheduleEmp = ref(true)
const selectedRow = ref(null)

// Выделенная строка табеля (объект записи) или null.
const selectedRowEntry = computed(() => {
  if (selectedRow.value === null || !tabel.value) return null
  return tabel.value.entries[selectedRow.value] ?? null
})

// Клик по строке табеля — выделить сотрудника (повторный клик — снять).
// Ячейки, поля ввода, кнопки и ссылки внутри строки останавливают всплытие
// события сами (см. @click.stop), поэтому выделение их не мешает.
function selectRow(idx) {
  selectedRow.value = selectedRow.value === idx ? null : idx
  const row = selectedRowEntry.value
  if (row) {
    message.value = `Выделен сотрудник: ${row.full_name}` +
      (row.tab_number ? ` (Таб. ${row.tab_number})` : '') +
      ' — нажмите «Заполнить сотрудника», чтобы заполнить месяц.'
    messageType.value = 'info'
  }
}

// Числа месяца для селектора даты: «15 (ср)».
const dayItems = computed(() => {
  if (!tabel.value) return []
  const list = []
  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    list.push({ title: `${d} (${getDayOfWeek(d)})`, value: d })
  }
  return list
})

// Список кодов справочника для диалогов ручного заполнения (v-combobox:
// можно и выбрать код, и ввести значение вручную).
const codeListItems = computed(() => cellItems.value.map(it => it.value))

// ─── Расписание дня сотрудника (для «Заполнить число» / «Заполнить сотрудника») ──
// daySchedule(row, d) возвращает значение, которым нужно заполнить день d
// согласно ГРАФИКУ работы сотрудника:
//   1) код из поля «Код для автозаполнения» (auto_fill_code) графика —
//      row.day_auto_codes[d] (например «8ч15м» в будни, «В» в выходные);
//   2) если кода нет, но норма дня > 0 и включён флаг «Часы по графику» —
//      подбирается код справочника по норме часов дня (codeForNormByRow:
//      8.25 → «8ч15м», 8 → «8», 7 → «7ч»; допуск ±0.5 ч; если точного кода
//      нет — используется числовое значение нормы, например «8.25»);
//   3) иначе '' — день пропускается (выходной без кода в графике).
function daySchedule(row, d) {
  const ac = dayAutoCode(row, d)
  if (ac) return ac
  const norm = getDayNorm(row, d)
  if (norm > 0) return codeForNormByRow(norm)
  return ''
}

// Подбор кода из справочника по норме часов конкретного дня/графика.
// Сначала ищется точное совпадение среди фиксированных кодов
// (hours_day + hours_night == норма): 8.25 → «8ч15м», 8 → «8», 7 → «7ч».
// При отсутствии точного — ближайший фиксированный код с допуском ±0.5 ч.
// Если подходящего кода нет, но в справочнике есть код с флагом «Время по
// графику» (use_schedule_hours) — используется он (сам подстроится под норму).
// Иначе — числовое значение нормы (например «8.25»).
function codeForNormByRow(norm) {
  const n = Number(norm) || 0
  if (n <= 0) return ''
  let best = null, bestDiff = Infinity
  for (const c of timeCodes.value) {
    if (c.use_schedule_hours) continue           // служебный fallback, не кандидат
    const h = (Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)
    if (h <= 0) continue
    const diff = Math.abs(h - n)
    if (diff > 0.5) continue
    // приоритет: меньший diff, затем более короткое название кода
    const tie = String(c.code).length
    if (diff < bestDiff - 1e-9 || (Math.abs(diff - bestDiff) < 1e-9 && (!best || tie < best.tie))) {
      best = { code: c.code, diff, tie }
      bestDiff = diff
    }
  }
  if (best) return best.code
  // Фиксированного кода нет — берём первый код с «Время по графику»…
  const sched = timeCodes.value.find(c => c.use_schedule_hours)
  if (sched) return sched.code
  // …иначе заполняем числовым значением нормы
  return String(Math.round(n * 100) / 100)
}

// Значение для режима «по графику» считается корректным, если это код из
// справочника ИЛИ числовое значение («8.25», «8ч15м», «8:15» — форматы,
// которые понимает валидатор ячеек rawToHours). Используется диалогами
// «Заполнить число» / «Заполнить сотрудника» при заполнении по графику.
function isValidScheduleValue(v) {
  if (!v || !String(v).trim()) return false
  const s = String(v).trim().replace(',', '.')
  if (codeSet().has(s.toLowerCase())) return true
  const h = rawToHours(s)
  return h !== null && h > 0 && h <= 23.59
}

// Эффективный набор значений для произвольного списка ячеек:
// mode='schedule' — по графику каждого сотрудника (daySchedule),
// mode='fixed'    — выбранный вручную код во все ячейки.
function resolveValues(cells, mode, fixedVal) {
  const res = []
  for (const { row, d } of cells) {
    const val = mode === 'schedule' ? daySchedule(row, d) : fixedVal
    if (!val) { res.push({ row, d, val: '', skip: true }); continue }
    if (mode === 'fixed' && !isValidValue(val)) { res.push({ row, d, val, skip: true }); continue }
    if (mode === 'schedule' && !isValidScheduleValue(val)) { res.push({ row, d, val, skip: true }); continue }
    res.push({ row, d, val, skip: false })
  }
  return res
}

// Общие предпросмотр/заполнение произвольного набора ячеек.
// resolved — результат resolveValues (уже с учётом графика/режима).
function previewResolved(resolved, overwrite) {
  let toFill = 0, skippedFilled = 0, skippedNoCode = 0
  for (const it of resolved) {
    if (it.skip) { skippedNoCode++; continue }
    const filled = !!(it.row.days[it.d] ?? '').toString().trim()
    if (filled && !overwrite) { skippedFilled++; continue }
    toFill++
  }
  return { toFill, skippedFilled, skippedNoCode }
}

function applyResolved(resolved, overwrite) {
  let filled = 0
  for (const it of resolved) {
    if (it.skip) continue
    const cur = (it.row.days[it.d] ?? '').toString().trim()
    if (cur && !overwrite) continue
    it.row.days[it.d] = it.val
    markDirty(it.row.employee_id, it.d)
    validateCell(it.row.employee_id, it.d)
    filled++
  }
  return filled
}

// Ячейки для «Заполнить число»: одна дата × все сотрудники.
const fillDayCells = computed(() => {
  if (!tabel.value || !fillDayDate.value) return []
  const d = fillDayDate.value
  return tabel.value.entries.map(row => ({ row, d }))
})

const fillDayResolved = computed(() =>
  resolveValues(fillDayCells.value, fillByScheduleDay.value ? 'schedule' : 'fixed',
    String(fillDayCode.value ?? '').trim()))

const fillDayPreview = computed(() => {
  const cells = fillDayCells.value
  const { toFill, skippedFilled, skippedNoCode } = previewResolved(fillDayResolved.value, overwriteExistingDay.value)
  return { total: cells.length, toFill, skippedFilled, skippedNoCode }
})

function openFillDayDialog() {
  overwriteExistingDay.value = true
  fillByScheduleDay.value = true
  // По умолчанию — сегодня, если этот день входит в месяц табеля
  const now = new Date()
  const inMonth = now.getFullYear() === tabel.value?.year &&
    (now.getMonth() + 1) === tabel.value?.month
  fillDayDate.value = inMonth ? now.getDate() : 1
  fillDayCode.value = ''
  fillDayDialog.value = true
}

function applyFillDay() {
  const modeSched = fillByScheduleDay.value
  const val = String(fillDayCode.value ?? '').trim()
  if (!modeSched && (!val || !isValidValue(val))) return
  const resolved = fillDayResolved.value
  const filled = applyResolved(resolved, overwriteExistingDay.value)
  if (filled === 0) {
    message.value = modeSched
      ? 'Нечего заполнять: в графике сотрудников нет кода для этой даты (или все ячейки заполнены — включите перезапись).'
      : 'Нечего заполнять: все ячейки за эту дату уже заполнены (включите перезапись).'
    messageType.value = 'warning'
    return
  }
  fillDayDialog.value = false
  message.value = `Заполнено: ${filled} ${pluralCells(filled)} за ${fillDayDate.value} ${monthNames[(tabel.value?.month ?? 1) - 1]} (${modeSched ? 'по графику сотрудников' : `код «${val}»`}). Нажмите «Сохранить», чтобы записать изменения.`
  messageType.value = 'success'
}

// Ячейки для «Заполнить сотрудника»: все дни месяца выделенной строки.
const fillEmpCells = computed(() => {
  const row = selectedRowEntry.value
  if (!row || !tabel.value) return []
  const cells = []
  for (let d = 1; d <= tabel.value.days_in_month; d++) cells.push({ row, d })
  return cells
})

const fillEmpResolved = computed(() =>
  resolveValues(fillEmpCells.value, fillByScheduleEmp.value ? 'schedule' : 'fixed',
    String(fillEmpCode.value ?? '').trim()))

const fillEmpPreview = computed(() => {
  const cells = fillEmpCells.value
  const { toFill, skippedFilled, skippedNoCode } = previewResolved(fillEmpResolved.value, overwriteExistingEmp.value)
  return { daysTotal: cells.length, toFill, skippedFilled, skippedNoCode }
})

function openFillEmployeeDialog() {
  if (selectedRow.value === null) return
  overwriteExistingEmp.value = true
  fillByScheduleEmp.value = true
  fillEmpCode.value = ''
  fillEmpDialog.value = true
}

function applyFillEmployee() {
  const row = selectedRowEntry.value
  if (!row) return
  const modeSched = fillByScheduleEmp.value
  const val = String(fillEmpCode.value ?? '').trim()
  if (!modeSched && (!val || !isValidValue(val))) return
  const resolved = fillEmpResolved.value
  const filled = applyResolved(resolved, overwriteExistingEmp.value)
  if (filled === 0) {
    message.value = modeSched
      ? 'Нечего заполнять: в графике этого сотрудника нет кодов автозаполнения (или все дни заполнены — включите перезапись).'
      : 'Нечего заполнять: все дни этого сотрудника уже заполнены (включите перезапись).'
    messageType.value = 'warning'
    return
  }
  fillEmpDialog.value = false
  message.value = `Заполнено: ${filled} ${pluralCells(filled)} для ${row.full_name} (${modeSched ? 'по индивидуальному графику' : `код «${val}»`}). Нажмите «Сохранить», чтобы записать изменения.`
  messageType.value = 'success'
}

// ИСПРАВЛЕНО: Добавлено свойство unit ('days' или 'hours') для точного расчета
// Колонка «Итого часов» намеренно НЕ последняя: после неё идут остальные
// итоговые колонки, а самой правой является «Часы по тарифу» (см. ниже).
const summaryColumns = ref([
  { key: 'fact_days', label: 'фактической работы', unit: 'days' },
  { key: 'total_hours', label: 'Итого часов', unit: 'hours' },
  { key: 'vacation', label: 'трудовой отпуск', unit: 'days' },
  { key: 'sick', label: 'болезнь', unit: 'days' },
  { key: 'admin_leave', label: 'с разрешения администрации', unit: 'days' },
  { key: 'weekend_holiday', label: 'выходные и праздн.', unit: 'days' },
  { key: 'other_absence', label: 'Другие неявки', unit: 'days' },
  { key: 'overtime_days', label: 'сверхурочные дни', unit: 'days' },
  { key: 'overtime_hours', label: 'Сверхурочные часы', unit: 'hours' },
  { key: 'night_hours', label: 'ночные часы', unit: 'hours' },
  { key: 'kdu_work_days', label: 'КДУ', unit: 'manual' },
  { key: 'kdu_weekend_days', label: 'КДУ вых. дня', unit: 'manual' },
  // Новая итоговая колонка «по тарифу» — крайняя справа (перед кнопкой удаления)
  { key: 'tariff_hours', label: 'Часы по тарифу', unit: 'hours' }
])

// Направления для справочника кодов («Куда попадёт»).
// Исправление: раньше список строился напрямую от summaryColumns, из-за чего
// в выпадающем списке не было «Часы по тарифу», а ночные/дневные часы были
// объединены в одну колонку. Ключи соответствуют логике calculateSummary:
// tariff_hours / night_hours / day_hours.
const destinationOptions = computed(() => {
  const opts = []
  for (const c of summaryColumns.value) {
    if (c.unit === 'manual') continue // КДУ заполняется вручную, не из кода
    if (c.key === 'tariff_hours' || c.key === 'night_hours') continue // добавляем явно ниже
    opts.push({ title: c.label, value: c.key })
    if (c.key === 'total_hours') {
      opts.push({ title: 'Часы по тарифу', value: 'tariff_hours' })
    }
  }
  opts.push({ title: 'Ночные часы', value: 'night_hours' })
  opts.push({ title: 'Дневные часы', value: 'day_hours' })
  return opts
})

function getDayOfWeek(day) {
  if (!tabel.value) return ''
  const date = new Date(tabel.value.year, tabel.value.month - 1, day)
  return dayOfWeekNames[date.getDay()]
}

const weekendSet = computed(() => new Set(tabel.value?.weekend_days || []))
const holidaySet = computed(() => new Set(tabel.value?.holiday_days || []))
function isWeekend(d) { return weekendSet.value.has(d) }
function isHoliday(d) { return holidaySet.value.has(d) }
function holidayName(d) {
  const n = tabel.value?.holiday_names?.[d]
  return n ? `${d}: ${n} — праздничный (нерабочий) день` : ''
}
const calendarNotLoaded = computed(() =>
  !!tabel.value && (tabel.value.holiday_days?.length ?? 0) === 0)

const allEmployees = ref([])
const selectedEmployee = ref(null)
let addingInProgress = false
let empSearchTimer = null

// Нормализация для поиска: нижний регистр + Ё->Е
const normSearch = s => String(s ?? '').toLowerCase().replace(/ё/g, 'е')

// Поиск по подстроке по всем полям: ФИО, табельный номер, подразделение.
// Регистронезависимо: «роман» находит и «Романов», и «Бельков Роман».
function empMatches(e, term) {
  const t = normSearch(term)
  return (
    normSearch(e.full_name).includes(t) ||
    normSearch(e.tab_number).includes(t) ||
    normSearch(e.department_name).includes(t)
  )
}

// Фильтрация внутри v-autocomplete (не через startsWith по умолчанию)
function filterEmployees(items, query) {
  if (!query || !query.trim()) return items.slice(0, 50)
  return items.filter(e => empMatches(e.raw ?? e, query)).slice(0, 50)
}

const employeeOptions = computed(() =>
  allEmployees.value.map(e => ({
    ...e,
    label: `${e.full_name}${e.tab_number ? ' — Таб. ' + e.tab_number : ''}${e.department_name ? ' — ' + e.department_name : ''}`
  }))
)

async function loadEmployees(q = '') {
  const { data } = await api.get('/tabels/search/employees', { params: { q } })
  const inTabel = new Set((tabel.value?.entries || []).map(r => r.employee_id))
  allEmployees.value = data.filter(e => !inTabel.has(e.id))
}

// Серверный поиск с debounce 300мс (минимум 1 символ)
function onEmpSearch(q) {
  clearTimeout(empSearchTimer)
  if (!q || q.trim().length < 1) return
  empSearchTimer = setTimeout(async () => {
    try { await loadEmployees(q.trim()) } catch (e) { /* ignore */ }
  }, 300)
}

async function onEmployeePicked(empId) {
  if (!empId || addingInProgress) return
  addingInProgress = true
  try {
    await api.post(`/tabels/${route.params.id}/employees`, { employee_ids: [empId] })
    await loadTabel()
    await loadEmployees()
  } catch (e) {
    message.value = e.response?.data?.detail || 'Ошибка добавления'
    messageType.value = 'error'
  } finally {
    selectedEmployee.value = null
    addingInProgress = false
  }
}

function codeSet() {
  return new Set(timeCodes.value.map(c => c.code.toLowerCase()))
}
function isCodeText(v) {
  return !!v && codeSet().has(String(v).trim().toLowerCase())
}

// ===== Tooltip для ячеек табеля =====
const MONTH_NAMES_RU_GENITIVE = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
const DAY_NAMES_RU_FULL = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

// Дата в tooltip: «Понедельник, 28 сентября 2026»
function tooltipDateLabel(day) {
  const t = tabel.value
  if (!t) return ''
  const date = new Date(t.year, t.month - 1, day)
  return `${DAY_NAMES_RU_FULL[date.getDay()]}, ${day} ${MONTH_NAMES_RU_GENITIVE[t.month - 1]} ${t.year}`
}

// Число без хвостовых нулей: 8.50 → «8.5», 8 → «8»
function fmtNum(n) {
  const v = Number(n) || 0
  return String(Number(v.toFixed(2)))
}

// Разбор числового значения ячейки («8.5», «8ч15м», «8:15») в часы
function rawToHours(s) {
  const str = String(s ?? '').trim().replace(',', '.')
  let m = str.match(/^(\d+(?:\.\d+)?)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return Number(m[1]) + (Number(m[2] || 0) / 60)
  m = str.match(/^(\d+)\s*:\s*(\d+)$/)
  if (m) return Number(m[1]) + Number(m[2]) / 60
  m = str.match(/^(\d+(?:\.\d+)?)$/)
  if (m) return Number(m[1])
  return null
}

// Данные для содержимого tooltip: код из справочника или числовое значение.
// Для числовых значений дополнительно показываем разбивку по норме (norm_hours):
// введено / норма / сверхурочные.
// Норма часов для конкретного дня месяца: из графика работы по дню недели.
// Если графика нет — fallback: employees.norm_hours, иначе 8.
function getDayNorm(row, d) {
  const dn = row && row.day_norms ? row.day_norms[d] : undefined
  if (dn !== undefined && dn !== null) return Number(dn) || 0
  return normOf(row)
}

// Эффективные часы кода для конкретного дня.
// Если у кода включено «Время по графику» (use_schedule_hours):
//  - будний день (норма > 0) — часы берутся из нормы графика (пн = 8.25ч и т.п.);
//  - выходной/праздник (норма = 0) — фиксированные weekend_hours из справочника
//    (например, 8 для «К»: командировка в выходной оплачивается как 8 часов).
// Иначе — фиксированные hours_day/hours_night из справочника.
function codeHoursForDay(codeObj, row, d) {
  if (!codeObj) return { day: 0, night: 0, total: 0 }
  if (codeObj.use_schedule_hours) {
    const norm = row ? getDayNorm(row, d) : 8
    if (norm <= 0) {
      // Выходной: используем «Часы для выходного дня», если заданы
      const we = Number(codeObj.weekend_hours)
      const weHours = Number.isFinite(we) && we > 0 ? we : 0
      return { day: weHours, night: 0, total: weHours }
    }
    return { day: norm, night: 0, total: norm }
  }
  const day = Number(codeObj.hours_day) || 0
  const night = Number(codeObj.hours_night) || 0
  return { day, night, total: day + night }
}

function cellTipData(val, row, d) {
  if (!val) return null
  const s = String(val).trim()
  const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) {
    const eff = codeHoursForDay(codeObj, row, d)
    const day = eff.day
    const night = eff.night
    const total = eff.total
    const dests = codeObj.destinations || []
    // Подсказка: «Время по графику» в выходной с фиксированными часами
    let schedNote = ''
    if (codeObj.use_schedule_hours && row) {
      const norm = getDayNorm(row, d)
      if (norm <= 0 && total > 0) {
        schedNote = `Выходной: ${hoursToHM(total)} (часы для выходного дня)`
      } else if (norm > 0) {
        schedNote = 'По графику'
      }
    }
    let ot = 0
    const normV = row ? getDayNorm(row, d) : null
    if (dests.includes('overtime_hours')) {
      // ИСПРАВЛЕНО: код сам является сверхурочным (например «8с» с направлением
      // overtime_hours) — ВСЕ его часы идут в сверхурочные (см. calculateSummary).
      ot = total
    } else if (row && total > 0 && codeObj.use_schedule_hours && normV !== null && normV <= 0) {
      // НОВОЕ: «Время по графику» + выходные часы (weekend_hours): работа в
      // законный выходной (норма = 0) — ВСЕ эти часы считаются сверхурочными.
      ot = total
    } else if (row && total > 0 && !codeObj.use_schedule_hours) {
      // Обычный код: сверхурочные = превышение над нормой графика.
      // Для «Время по графику» в будний день часы == норма → сверхурочных нет.
      ot = Math.max(0, total - normV)
    }
    return { kind: 'code', code: codeObj.code, name: codeObj.name, day, night, total, ot, schedNote }
  }
  const hours = rawToHours(s)
  if (hours !== null) {
    const norm = row ? getDayNorm(row, d) : 8
    const ot = Math.max(0, hours - norm)
    return { kind: 'number', hours, norm, regular: Math.min(hours, norm), ot }
  }
  return null
}

// Фоновая подсветка ячейки, если часов больше нормы (жёлтый — есть сверхурочные)
function isOvertimeCell(row, val, d) {
  const data = cellTipData(val, row, d)
  return !!data && data.ot > 0
}

// Текст для пустой ячейки (доступен программно; tooltip для пустых ячеек отключён через :disabled)
function cellTipText(val) {
  if (!val) return 'Ячейка пустая. Кликните для выбора кода.'
  return ''
}

function hoursToHM(h) {
  const total = Math.round((Number(h) || 0) * 60)
  if (!total) return '0м'
  const hh = Math.floor(total / 60)
  const mm = total % 60
  if (hh && mm) return `${hh}ч${mm}м`
  if (hh) return `${hh}ч`
  return `${mm}м`
}

const cellItems = computed(() => {
  return timeCodes.value.map(c => {
    let hrs = ''
    if (c.use_schedule_hours) {
      hrs = ' (по графику)'
    } else {
      const h = (Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)
      hrs = h ? ` (${hoursToHM(h)})` : ''
    }
    return {
      title: `${c.code} — ${c.name}${hrs}`,
      value: c.code,
    }
  })
})

function cellFilter(value, query) {
  if (!query) return true
  const q = String(query).toLowerCase().replace(',', '.')
  const v = String(value ?? '').toLowerCase().replace(',', '.')
  return v.startsWith(q) || v.includes(q)
}

const openCell = ref(null)
const cellQuery = ref('')
const menuX = ref(0)
const menuY = ref(0)

const filteredCellItems = computed(() => {
  const q = cellQuery.value.trim().toLowerCase().replace(',', '.')
  if (!q) return cellItems.value
  return cellItems.value.filter(it => cellFilter(it.value, q))
})

function openCellPicker(empId, day, event) {
  const key = empId + '_' + day
  if (openCell.value === key) { openCell.value = null; return }
  menuX.value = event?.clientX ?? 0
  menuY.value = (event?.clientY ?? 0) + 24
  openCell.value = key
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  cellQuery.value = row?.days[day] || ''
}

function pickCellValue(empId, day, val) {
  const text = String(val ?? '').trim()
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row) row.days[day] = text
  markDirty(empId, day)
  validateCell(empId, day)
  openCell.value = null
  cellQuery.value = ''
}

// Очистка ячейки: значение удаляется, ячейка становится пустой,
// изменение помечается dirty, меню закрывается.
function clearCell(empId, day) {
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row) row.days[day] = ''
  markDirty(empId, day)
  validateCell(empId, day)
  openCell.value = null
  cellQuery.value = ''
}

function isValidValue(v) {
  if (!v || !v.trim()) return true
  const s = v.trim().replace(',', '.')
  if (codeSet().has(s.toLowerCase())) return true
  if (/^\d{1,2}(\.\d{1,2})?$/.test(s)) {
    const n = parseFloat(s)
    return n > 0 && n <= 23.59
  }
  return false
}

function hasError(empId, day) {
  return !!cellErrors.value[`${empId}_${day}`]
}

function validateCell(empId, day) {
  const key = `${empId}_${day}`
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  if (row && !isValidValue(row.days[day])) cellErrors.value[key] = true
  else delete cellErrors.value[key]
}

function markDirty(empId, day) {
  const row = tabel.value.entries.find(r => r.employee_id === empId)
  dirty.value[`${empId}_${day}`] = row ? row.days[day] : ''
}

// ─── Логика «Заполнить по графику» ────────────────────────────────────────

// ИСПРАВЛЕНО: код больше НЕ подбирается по часам — он берётся напрямую из
// поля «Код для автозаполнения» (auto_fill_code) каждого дня недели графика
// работы сотрудника. Бэкенд отдаёт его в row.day_auto_codes (по дням месяца).
// Если код в графике не указан — день пропускается.
// ВАЖНО: выходные и праздники (норма 0 ч) ТАКЖЕ заполняются, если для них в
// графике задан код (например «В» — выходной). Раньше условие «норма > 0»
// блокировало простановку «В» на Сб/Вс — исправлено.

// Код автозаполнения из графика для конкретного дня месяца ('' если не задан).
function dayAutoCode(row, d) {
  const dac = row && row.day_auto_codes ? row.day_auto_codes[d] : undefined
  return dac == null ? '' : String(dac).trim()
}

// День участвует в автозаполнении, если в графике задан код (любая норма,
// включая 0 — выходные/праздники с кодом «В»).
function isFillableDay(row, d) {
  return dayAutoCode(row, d) !== ''
}

// Дни, для которых есть норма, но нет кода в графике (для предупреждения).
const fillMissingCodes = computed(() => {
  const set = new Set()
  if (!tabel.value) return []
  for (const row of tabel.value.entries) {
    for (let d = 1; d <= tabel.value.days_in_month; d++) {
      if (getDayNorm(row, d) > 0 && dayAutoCode(row, d) === '') set.add(getDayNorm(row, d))
    }
  }
  return [...set].sort((a, b) => a - b)
})

// Предпросмотр: сколько ячеек будет заполнено / пропущено (по каждому сотруднику).
const fillPreview = computed(() => {
  let workDaysTotal = 0, toFill = 0, skippedFilled = 0, skippedNoCode = 0
  if (!tabel.value) return { workDaysTotal, toFill, skippedFilled, skippedNoCode }
  for (const row of tabel.value.entries) {
    for (let d = 1; d <= tabel.value.days_in_month; d++) {
      const norm = getDayNorm(row, d)
      if (dayAutoCode(row, d) === '') {                 // в графике нет кода — пропускаем
        if (norm > 0) { workDaysTotal++; skippedNoCode++ }
        continue
      }
      workDaysTotal++                                   // рабочий день или выходной с кодом («В»)
      const filled = !!(row.days[d] ?? '').toString().trim()
      if (filled && !overwriteExisting.value) { skippedFilled++; continue }
      toFill++
    }
  }
  return { workDaysTotal, toFill, skippedFilled, skippedNoCode }
})

function openFillByScheduleDialog() {
  // Сброс настроек диалога перед открытием
  overwriteExisting.value = true
  fillDialog.value = true
}

function applyFillBySchedule() {
  if (!tabel.value) return
  let filled = 0
  for (const row of tabel.value.entries) {
    for (let d = 1; d <= tabel.value.days_in_month; d++) {
      const val = dayAutoCode(row, d)                    // код напрямую из графика
      if (!val) continue                                 // код не указан в графике — пропускаем
      // ИСПРАВЛЕНО: дни с нормой 0 (выходные/праздники) БОЛЬШЕ не пропускаются —
      // если в графике задан код (например «В»), он подставляется и в эти дни.
      const cur = (row.days[d] ?? '').toString().trim()
      if (cur && !overwriteExisting.value) continue      // не перезаписываем без галочки
      row.days[d] = val
      markDirty(row.employee_id, d)                      // помечаем ячейку для сохранения
      validateCell(row.employee_id, d)
      filled++
    }
  }
  if (filled === 0) {
    message.value = 'Нечего заполнять: проверьте «Код для автозаполнения» в графиках работы и флаг перезаписи.'
    messageType.value = 'warning'
    return
  }
  fillDialog.value = false
  const extra = fillPreview.value.skippedNoCode
    ? ` Внимание: для ${fillPreview.value.skippedNoCode} рабочих дней в графике не указан код — они пропущены.`
    : ''
  message.value = `Табель заполнен по кодам из графиков: ${filled} ${pluralCells(filled)}. Нажмите «Сохранить», чтобы записать изменения.${extra}`
  messageType.value = fillPreview.value.skippedNoCode ? 'warning' : 'success'
}

// Склонение слова «ячейка»: 1 ячейка, 2-4 ячейки, 5+ ячеек.
function pluralCells(n) {
  const m10 = n % 10, m100 = n % 100
  if (m10 === 1 && m100 !== 11) return 'ячейка'
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'ячейки'
  return 'ячеек'
}

function cellMinutes(v, row, d) {
  const s = String(v ?? '').trim().toLowerCase().replace(/,/g, '.')
  if (!s) return 0
  let m = s.match(/^(\d+)\s*ч\s*(\d+)?\s*м?$/)
  if (m) return parseInt(m[1]) * 60 + (m[2] ? parseInt(m[2]) : 0)
  m = s.match(/^(\d+)\s*м$/)
  if (m) return parseInt(m[1])
  m = s.match(/^(\d+):([0-5]\d)$/)
  if (m) return parseInt(m[1]) * 60 + parseInt(m[2])
  if (/^\d+(\.\d+)?$/.test(s)) return Math.round(parseFloat(s) * 60)
  const c = timeCodes.value.find(x => x.code.toLowerCase() === s)
  if (c) {
    // «Время по графику»: часы = норма графика на этот день (если есть контекст дня)
    if (c.use_schedule_hours && row && d) return Math.round(codeHoursForDay(c, row, d).total * 60)
    return Math.round(((Number(c.hours_day) || 0) + (Number(c.hours_night) || 0)) * 60)
  }
  return 0
}

function totalHours(row) {
  let minutes = 0
  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    minutes += cellMinutes(row.days[d], row, d)
  }
  const hh = Math.floor(minutes / 60)
  const mm = minutes % 60
  return mm ? `${hh}ч${mm}м` : `${hh}ч`
}

// ИСПРАВЛЕНО: Расчет теперь использует свойство unit из summaryColumns
// Колонки с unit === 'manual' (КДУ) заполняются вручную и здесь не считаются.
// Часы сверх нормы (norm_hours, по умолчанию 8) автоматически уходят в сверхурочные:
// «Итого часов» = все часы; «по тарифу» (тарифные часы) = только обычные; превышение — в overtime_*.
function cellHoursForDay(row, val) {
  const s = String(val ?? '').trim()
  if (!s) return null
  const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === s.toLowerCase())
  if (codeObj) {
    // код справочника НЕ считаем числовыми часами (например «7» — это Выходной)
    return null
  }
  return rawToHours(s)
}

function normOf(row) {
  const n = Number(row && row.norm_hours)
  return n > 0 ? n : 8
}

function calculateSummary(row) {
  const summary = {}
  summaryColumns.value.forEach(col => { if (col.unit !== 'manual') summary[col.key] = 0 })

  for (let d = 1; d <= tabel.value.days_in_month; d++) {
    const val = String(row.days[d] || '').trim()
    if (!val) continue

    // Норма по графику работы для этого дня недели (fallback: employees.norm_hours или 8)
    const norm = getDayNorm(row, d)

    const hours = cellHoursForDay(row, val)
    if (hours !== null && hours > 0) {
      // числовой ввод: обычные часы + сверхурочные сверх нормы по графику.
      // ИСПРАВЛЕНО: «Сверхурочные дни» при числовом вводе НЕ добавляются —
      // в эту колонку попадают только коды справочника с направлением overtime_days.
      const regular = Math.min(hours, norm)
      const ot = Math.max(0, hours - norm)
      summary.total_hours += hours
      summary.fact_days += 1
      summary.tariff_hours += regular
      if (ot > 0) {
        summary.overtime_hours += ot
      }
      continue
    }

    const codeObj = timeCodes.value.find(c => c.code.toLowerCase() === val.toLowerCase())
    if (codeObj) {
      // «Время по графику»: часы кода = норма графика на этот день (см. codeHoursForDay)
      const eff = codeHoursForDay(codeObj, row, d)
      const hoursDay = eff.day
      const hoursNight = eff.night
      const totalHours = eff.total
      const dests = codeObj.destinations || []

      dests.forEach(dest => {
        const colDef = summaryColumns.value.find(c => c.key === dest)
        if (colDef && summary.hasOwnProperty(dest)) {
          if (colDef.unit === 'days') {
            summary[dest] += 1
          } else if (dest === 'night_hours') {
            summary[dest] += hoursNight
          } else if (dest === 'day_hours') {
            summary[dest] += hoursDay
          } else if (dest === 'overtime_hours') {
            // ИСПРАВЛЕНО: код с направлением overtime_hours (например «8с») —
            // сверхурочный код, ВСЕ его часы идут в «Сверхурочные часы»,
            // а не только превышение над нормой.
            summary[dest] += totalHours
          } else {
            summary[dest] += totalHours
          }
        }
      })

      // ИСПРАВЛЕНО: логика сверхурочных ЧАСОВ и ДНЕЙ разделена.
      // Сверхурочные часы: обычные коды (без собственных направлений overtime_*)
      // дают переработку = фактические часы кода минус норма по графику
      // (getDayNorm); tooltip (cellTipData) считает так же → значения совпадают.
      // Коды с направлением 'overtime_hours' уже добавили ВСЕ свои часы в
      // «Сверхурочные часы» в цикле dests.forEach выше — повторно не считаем.
      // Сверхурочные дни: добавляются ТОЛЬКО если код имеет направление
      // 'overtime_days' в справочнике (см. цикл dests.forEach выше). Превышение
      // нормы само по себе день в колонку «сверхурочные дни» не попадает
      // (например, код "8" при норме 8.25).
      const isOvertimeCode = dests.includes('overtime_hours') || dests.includes('overtime_days')
      if (codeObj.use_schedule_hours && !isOvertimeCode && norm <= 0 && totalHours > 0) {
        // НОВОЕ: «Время по графику» + «Часы для выходного дня»: работа в законный
        // выходной (норма = 0). Эти часы — сверхурочные: добавляем их в
        // «Сверхурочные часы», даже если у кода нет направления overtime_hours.
        summary.overtime_hours += totalHours
      } else if (totalHours > 0 && !isOvertimeCode && !codeObj.use_schedule_hours) {
        const ot = Math.max(0, totalHours - norm)
        if (ot > 0) {
          summary.overtime_hours += ot
          // из колонок обычных часов вычитаем превышение, если код туда попал
          if (dests.includes('tariff_hours')) summary.tariff_hours = Math.max(0, summary.tariff_hours - ot)
          // «Итого часов» остаётся полным (все введённые часы)
        }
      }
    }
  }

  // Округление на основе типа единицы измерения
  for (const key in summary) {
    const colDef = summaryColumns.value.find(c => c.key === key)
    if (colDef) {
      if (colDef.unit === 'hours') {
        summary[key] = Math.round(summary[key] * 100) / 100
      } else {
        summary[key] = Math.round(summary[key]) // Дни всегда целые
      }
    }
  }

  return summary
}

// ===== Ручные колонки КДУ (0..5, точность до сотых) =====
function clampKdu(raw) {
  if (raw === '' || raw === null || raw === undefined) return null
  let n = parseFloat(String(raw).replace(',', '.'))
  if (Number.isNaN(n)) return null
  // автокоррекция: <0 → 0, >5 → 5, округление до сотых (2.567 → 2.57)
  n = Math.min(5, Math.max(0, n))
  return Math.round(n * 100) / 100
}

// КДУ-ключи содержат подчёркивания внутри имени поля (kdu_work_days), поэтому
// employee_id выделяется НЕ по lastIndexOf('_') — иначе из "12_kdu_work_days"
// получались empId=NaN и field="days" → 422 «employee_id должен быть integer» и
// «Недопустимое поле КДУ». Надёжнее хранить employee_id и field отдельно.

// Отметка изменения КДУ. Ключ — `${employee_id}_${field}`, где employee_id
// обязательно приводится к числу: если в данных строки id пришёл строкой ("12"),
// шаблонный ключ давал бы "NaN_kdu_work_days" и employee_id в payload становился
// null → 422 «Input should be a valid integer» на /tabels/{id}/kdu.
function markKduDirty(row, field, value) {
  const empId = Number(row.employee_id)
  if (!Number.isInteger(empId)) return
  dirtyKdu.value[`${empId}_${field}`] = value
}

// Разбор ключа вида "{employeeId}_{fieldName}". Поле ищем по известному
// суффиксу (whitelist), а не по последнему подчёркиванию — суффикс может
// содержать подчёркивания ("kdu_work_days").
const KDU_FIELDS = ['kdu_work_days', 'kdu_weekend_days']
function parseKduKey(key) {
  const k = String(key)
  for (const f of KDU_FIELDS) {
    if (k.endsWith('_' + f)) {
      const empId = Number(k.slice(0, k.length - f.length - 1))
      if (Number.isInteger(empId)) return { empId, field: f }
      return null
    }
  }
  return null
}

function onKduInput(row, field, event) {
  const raw = event.target.value
  const clamped = clampKdu(raw)
  row[field] = clamped
  // мгновенная автокоррекция значений вне диапазона (6 → 5)
  if (clamped !== null && String(clamped) !== raw.replace(',', '.')) {
    event.target.value = clamped
  }
  markKduDirty(row, field, clamped)
}

function onKduBlur(row, field) {
  const clamped = clampKdu(row[field])
  row[field] = clamped
  markKduDirty(row, field, clamped)
}

async function loadTabel() {
  const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const id = Number(raw)
  if (!Number.isInteger(id) || id <= 0) {
    console.error('Некорректный id табеля в URL:', raw)
    message.value = 'Некорректный адрес табеля'
    messageType.value = 'error'
    return
  }
  try {
    const { data } = await api.get(`/tabels/${id}`)
    // инициализация полей КДУ, если их нет (старые данные)
    ;(data.entries || []).forEach(e => {
      if (!('kdu_work_days' in e)) e.kdu_work_days = null
      if (!('kdu_weekend_days' in e)) e.kdu_weekend_days = null
      // Норма часов: основная — из графика (day_norms по дням месяца);
      // norm_hours сотрудника — только fallback, если график не назначен.
      if (!('norm_hours' in e)) e.norm_hours = null
      if (!e.day_norms) e.day_norms = {}
      // Коды автозаполнения из графика («Код для автозаполнения» по дням месяца)
      if (!e.day_auto_codes) e.day_auto_codes = {}
    })
    tabel.value = data
    dirty.value = {}
    dirtyKdu.value = {}
    cellErrors.value = {}
  } catch (e) {
    const status = e.response?.status
    const detail = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail
      : (status ? `Ошибка сервера ${status} при загрузке табеля` : 'Сеть недоступна')
    message.value = detail
    messageType.value = 'error'
    if (status === 401 && auth.isAuthenticated?.()) {
      auth.logout?.()
      window.location.href = '/login'
    }
  }
}

async function removeEmployee(row) {
  if (!confirm(`Убрать ${row.full_name} из табеля?`)) return
  await api.delete(`/tabels/${route.params.id}/entries/${row.employee_id}`)
  await loadTabel()
  await loadEmployees()
}

// Сохранение изменённых ячеек дней через PUT /tabels/{id}/cells.
// Отбираются ТОЛЬКО корректные записи с числовым employee_id и day — защита от
// случайного попадания в payload ячеек/полей другого типа (например, КДУ).
// Возвращает true при успехе (или если изменений нет), иначе выбрасывает ошибку.
async function saveDayCells() {
  const updates = []
  for (const [key, value] of Object.entries(dirty.value)) {
    const parts = String(key).split('_')
    if (parts.length !== 2) continue
    const empId = Number(parts[0])
    const day = Number(parts[1])
    if (!Number.isInteger(empId) || !Number.isInteger(day)) continue
    updates.push({ employee_id: empId, day, value: String(value ?? '') })
  }
  // Если после фильтрации не осталось ни одной корректной ячейки — изменения просто
  // сбрасываются. Важно НЕ вызывать PUT /cells с пустым списком: бэкенд вернёт 422
  // («Input should be a valid integer, input: []»), что блокировало бы и сохранение КДУ.
  if (!updates.length) { dirty.value = {}; return true }
  await api.put(`/tabels/${route.params.id}/cells`, updates)
  dirty.value = {}
  return true
}

// Сохранение ручных значений КДУ отдельно от ячеек дней — через PUT /tabels/{id}/kdu.
async function saveKdu() {
  const kduUpdates = []
  for (const [key, value] of Object.entries(dirtyKdu.value)) {
    // В payload попадают только допустимые поля КДУ и корректный employee_id.
    // Разбор по whitelist-суффиксу: имена полей содержат подчёркивания.
    const parsed = parseKduKey(key)
    if (!parsed) continue
    kduUpdates.push({ employee_id: parsed.empId, field: parsed.field, value })
  }
  if (!kduUpdates.length) { dirtyKdu.value = {}; return true }
  try {
    await api.put(`/tabels/${route.params.id}/kdu`, kduUpdates)
  } catch (e) {
    // Понятная ошибка, если бэкенд ещё не поддерживает endpoint /kdu
    if (e.response?.status === 404 || e.response?.status === 405) {
      throw new Error('Бэкенд не поддерживает сохранение КДУ (endpoint /tabels/{id}/kdu не найден). Обновите серверную часть.')
    }
    // 422 — значит на сервер ушёл некорректный payload или там крутится старая
    // версия бэкенда без валидной схемы KduUpdate.
    if (e.response?.status === 422) {
      throw new Error('Сервер отклонил данные КДУ (422). Проверьте, что backend обновлён: PUT /tabels/{id}/kdu принимает [{employee_id, field, value}].')
    }
    throw e
  }
  dirtyKdu.value = {}
  return true
}

async function save(showMsg = true) {
  const hasCellChanges = Object.keys(dirty.value).length > 0
  const hasKduChanges = Object.keys(dirtyKdu.value).length > 0
  if (!hasCellChanges && !hasKduChanges) {
    if (showMsg) {
      message.value = 'Нет несохранённых изменений'
      messageType.value = 'success'
      setTimeout(() => { if (message.value === 'Нет несохранённых изменений') message.value = '' }, 2000)
    }
    return true
  }
  if (Object.keys(cellErrors.value).length) {
    message.value = 'Есть некорректные ячейки — исправьте их перед сохранением'
    messageType.value = 'error'
    return false
  }
  saving.value = true
  const errors = []
  try {
    // Ячейки дней и КДУ сохраняются НЕЗАВИСИМО друг от друга: сбой одной операции
    // не должен блокировать другую (раньше ошибка /cells или /kdu прерывала всё
    // сохранение по try/catch, из-за чего «кнопка Сохранить не работала» и КДУ
    // не сохранялся).
    if (hasCellChanges) {
      try { await saveDayCells() }
      catch (e) { errors.push('Ячейки дней: ' + describeSaveError(e)) }
    }
    if (hasKduChanges) {
      try { await saveKdu() }
      catch (e) { errors.push('КДУ: ' + describeSaveError(e)) }
    }
    if (errors.length) {
      message.value = errors.join(' | ')
      messageType.value = 'error'
      return false
    }
    if (showMsg) {
      message.value = 'Сохранено'
      messageType.value = 'success'
      setTimeout(() => { if (message.value === 'Сохранено') message.value = '' }, 2000)
    }
    return true
  } finally {
    saving.value = false
  }
}

// Человекочитаемое описание ошибки сохранения (в т.ч. pydantic-валидаторы бэкенда)
function describeSaveError(e) {
  if (e instanceof Error && !e.response) return e.message
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0]
    const field = Array.isArray(first?.loc) ? first.loc.join('.') : ''
    return `${first?.msg || 'Ошибка валидации данных'}${field ? ` (${field})` : ''}`
  }
  return e.message || 'Ошибка сохранения'
}

function codesForRow(row) {
  const used = new Set()
  Object.values(row.days || {}).forEach(v => {
    const t = String(v || '').trim().toLowerCase()
    if (!t) return
    const c = timeCodes.value.find(x => x.code.toLowerCase() === t)
    if (c) used.add(c.code)
  })
  return Array.from(used).map(code => timeCodes.value.find(x => x.code === code))
}

async function loadCodes() {
  try {
    const { data } = await api.get('/time-codes/')
    timeCodes.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('Не удалось загрузить справочник кодов часов', e)
  }
}

function editCode(c) {
  isEditing.value = true
  editingCode.value = c
  newCode.value = {
    code: c.code,
    name: c.name,
    hours_day: c.hours_day,
    hours_night: c.hours_night,
    use_schedule_hours: !!c.use_schedule_hours,
    weekend_hours: (c.weekend_hours == null || c.weekend_hours === '') ? null : Number(c.weekend_hours),
    destinations: [...(c.destinations || [])]
  }
  codeError.value = ''
}

function cancelEdit() {
  isEditing.value = false
  editingCode.value = null
  newCode.value = { code: '', name: '', hours_day: 0, hours_night: 0, use_schedule_hours: false, weekend_hours: null, destinations: [] }
  codeError.value = ''
}

async function saveCode() {
  codeError.value = ''
  try {
    if (isEditing.value && editingCode.value) {
      await api.put(`/time-codes/${editingCode.value.id}`, newCode.value)
    } else {
      await api.post('/time-codes/', newCode.value)
    }
    cancelEdit()
    await loadCodes()
  } catch (e) {
    codeError.value = typeof e.response?.data?.detail === 'string'
      ? e.response.data.detail : 'Ошибка сохранения кода'
  }
}

async function deleteCode(c) {
  if (!confirm(`Удалить код «${c.code}»?`)) return
  await api.delete(`/time-codes/${c.id}`)
  await loadCodes()
}

// Авто-сохранение раз в 30 секунд (только ячеек дней и КДУ, без всплывающего
// сообщения). Ошибки автосохранения не перекрывают уже показанное сообщение
// об успехе ручного сохранения.
const autoSaveTimer = setInterval(() => {
  if (Object.keys(dirty.value).length || Object.keys(dirtyKdu.value).length) save(false)
}, 30000)

// При уходе со страницы (SPA-навигация) — если есть несохранённые изменения
// (в т.ч. КДУ), сохраняем их, чтобы значения не «сбрасывались» после перезахода.
onBeforeUnmount(() => {
  clearInterval(autoSaveTimer)
  window.removeEventListener('beforeunload', onWindowUnload)
  if (Object.keys(dirty.value).length || Object.keys(dirtyKdu.value).length) save(false)
})

// Если пользователь закрыл вкладку/перезагрузил страницу с несохранённым КДУ —
// пробуем отправить изменения до выгрузки страницы. Обычный async-запрос в этот
// момент браузером прерывается, поэтому используется navigator.sendBeacon.
// Важно: endpoint /kdu требует аутентификацию, а sendBeacon не может добавить
// заголовок Authorization — вместо этого токен передаётся через query-параметр
// access_token (FastAPI OAuth2PasswordBearer его принимает).
function onWindowUnload() {
  const kduEntries = Object.entries(dirtyKdu.value)
  if (!kduEntries.length) return
  const payload = []
  for (const [key, value] of kduEntries) {
    const parsed = parseKduKey(key)
    if (!parsed) continue
    payload.push({ employee_id: parsed.empId, field: parsed.field, value })
  }
  if (!payload.length) return
  try {
    const raw = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
    const token = localStorage.getItem('token') || ''
    const url = `${api.defaults.baseURL}/tabels/${raw}/kdu?access_token=${encodeURIComponent(token)}`
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
    navigator.sendBeacon(url, blob)
  } catch (e) { /* ignore */ }
}
window.addEventListener('beforeunload', onWindowUnload)

onMounted(async () => {
  await Promise.all([loadTabel(), loadCodes()])
  await loadEmployees()
})
</script>

<style scoped>
/* Tooltip для ячеек табеля */
.day-tooltip {
  font-size: 12px;
  line-height: 1.5;
  padding: 4px 2px;
}
.tooltip-divider {
  opacity: 0.3;
}
.cell-tip-area {
  display: block;
  width: 100%;
  height: 100%;
}
.tabel-scroll {
  /* Двумерная прокрутка: шапка (дни/числа) и колонки №/ФИО закреплены */
  overflow: auto;
  max-height: calc(100vh - 260px);
}
.tabel-table {
  border-collapse: separate;  /* обязательно для position:sticky с border-collapse */
  border-spacing: 0;
  font-size: 12px;
  white-space: nowrap;
}
.tabel-table th, .tabel-table td {
  border: 1px solid #000;
  padding: 2px;
}

.tabel-table thead th {
  background-color: white !important;
  color: black !important;
  font-weight: bold;
  text-align: center;
  vertical-align: middle;
}

.col-no { width: 40px; min-width: 40px; max-width: 40px; text-align: center; font-size: 11px; }
.col-fio { min-width: 200px; width: 200px; max-width: 200px; text-align: left; padding-left: 6px !important; }
.col-days-header { font-size: 13px; font-weight: bold; padding: 4px !important; }
.col-day-header { width: 38px; min-width: 38px; max-width: 38px; padding: 2px 1px !important; font-size: 10px; }
.day-name { font-size: 9px; font-weight: normal; color: #666; }
.day-number { font-size: 11px; font-weight: bold; }
.day-weekend-header { background-color: #f0f0f0 !important; }
.day-holiday-header { background-color: #fff3cd !important; }

/* ================= ЗАКРЕПЛЕНИЕ ШАПКИ И КОЛОНОК (sticky) ================= */
/* Первый уровень шапки — прижат к верху области прокрутки */
.tabel-table th.sticky-top {
  position: sticky; top: 0; z-index: 5;
}
/* Второй уровень шапки (дни/числа) — под первым (учитывая бордер первого ряда) */
.tabel-table th.sticky-top-l2 {
  position: sticky; top: 41px; z-index: 4;
}
/* Колонка № п/п — закреплена слева (первая) */
.tabel-table .sticky-left-1 {
  position: sticky; left: 0; z-index: 3;
}
/* Колонка ФИО — закреплена слева (вторая, со сдвигом на ширину № + бордер) */
.tabel-table .sticky-left-2 {
  position: sticky; left: 42px; z-index: 3;
}
/* Правая колонка действий — закреплена справа */
.tabel-table .sticky-right {
  position: sticky; right: 0; z-index: 3;
}
/* Пересечения «шапка × боковые колонки» — поверх остальных sticky-слоёв */
.tabel-table th.sticky-top.sticky-left-1,
.tabel-table th.sticky-top.sticky-left-2,
.tabel-table th.sticky-top.sticky-right { z-index: 7; }
/* Непрозрачные фоны, чтобы при прокрутке ячейки не просвечивали сквозь закреплённые cells */
.tabel-table .col-no.sticky-left-1,
.tabel-table .col-fio.sticky-left-2,
.tabel-table td.col-del.sticky-right { background-color: white; }
.tabel-table tr.add-row .sticky-left-1,
.tabel-table tr.add-row .sticky-left-2 { background-color: #f9fbe7; }
/* Выделенная строка сотрудника (клик по строке — для «Заполнить сотрудника»):
   синяя подсветка всех ячеек, включая закреплённые sticky-колонки */
.tabel-table tbody tr.row-selected td { background-color: #e3f2fd !important; }
.tabel-table tbody tr:hover td { cursor: pointer; }
/* Заполнение sticky-ячейки на всю высоту строки (равномерный фон и рамка) */
.sticky-fill {
  position: relative; z-index: 1;
  display: flex; align-items: center; justify-content: center;
  height: 100%; min-height: 24px;
}
td.col-fio.sticky-left-2 > .sticky-fill { justify-content: flex-start; }
/* Выходные/праздники в закреплённых колонках сохраняют свой цвет фона */
.cell-weekend.sticky-left-1, .cell-weekend.sticky-left-2 { background-color: #f0f0f0; }
.cell-holiday.sticky-left-1, .cell-holiday.sticky-left-2 { background-color: #fff3cd; }
/* Тонкая тень у границы закреплённой зоны для читаемости */
.tabel-table .sticky-left-2::after {
  content: ''; position: absolute; top: 0; bottom: -1px; right: -9px; width: 8px;
  pointer-events: none; box-shadow: inset -6px 0 6px -6px rgba(0, 0, 0, 0.25); z-index: 2;
}
.tabel-table th.sticky-top-l2::after {
  content: ''; position: absolute; left: 0; right: -1px; bottom: -9px; height: 8px;
  pointer-events: none; box-shadow: inset 0 -6px 6px -6px rgba(0, 0, 0, 0.25); z-index: 2;
}

.col-summary-header {
  width: 28px; min-width: 28px; max-width: 28px; padding: 8px 2px !important;
  font-size: 10px; font-weight: bold; text-align: center;
  writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg);
  white-space: nowrap; vertical-align: middle;
  background-color: white !important; border-left: 1px solid #000 !important;
}

.col-summary-cell {
  width: 28px; min-width: 28px; max-width: 28px; padding: 2px 1px !important;
  font-size: 11px; font-weight: normal; text-align: center;
  background-color: white !important; border-left: 1px solid #000 !important;
}

/* Ручные колонки КДУ — визуально отличаются (зелёный фон input) */
.kdu-input {
  width: 100%; box-sizing: border-box;
  border: 1px solid #a5d6a7; border-radius: 4px;
  background-color: #e8f5e9;
  font-size: 11px; text-align: center; padding: 2px 1px;
  outline: none;
}
.kdu-input:focus { border-color: #2e7d32; background-color: #f1f8e9; }
/* скрыть стрелки number-инпута, чтобы не ломать узкую колонку */
.kdu-input::-webkit-outer-spin-button,
.kdu-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.kdu-input[type=number] { -moz-appearance: textfield; appearance: textfield; }

.col-del { width: 40px; background-color: white !important; }
.cell-day { width: 38px; min-width: 38px; max-width: 38px; padding: 2px !important; }
.cell-weekend { background-color: #f0f0f0; }
.cell-holiday { background-color: #fff3cd; }
.holiday-mark { font-size: 10px; margin-left: 1px; vertical-align: top; }

.legend-box { display: inline-block; width: 14px; height: 14px; border-radius: 3px; border: 1px solid #c8e6c9; vertical-align: middle; margin-right: 4px; }
.legend-weekend { background-color: #f0f0f0; }
.legend-holiday { background-color: #fff3cd; }

.cell-wrap { position: relative; width: 100%; height: 24px; }
.cell-input {
  width: 100%; height: 24px; box-sizing: border-box; border: none; outline: none;
  background: transparent; text-align: center; font-size: 12px; font-family: inherit;
  cursor: pointer; color: rgba(0, 0, 0, 0.87);
}
.cell-input:hover { background: #e8f5e9; }
.cell-wrap.is-open .cell-input { background: #e8f5e9; box-shadow: inset 0 0 0 2px #2d5a3d; }
.is-code { color: #1565c0; font-weight: bold; }
/* Ячейка с часами сверх нормы (есть сверхурочные) — жёлтая подсветка */
.is-overtime-cell { background: #fff9c4 !important; box-shadow: inset 0 -2px 0 #f9a825; }
.is-error, .is-error-cell { background: #ffebee !important; outline: 2px solid red; }
.add-row td { border-top: 2px dashed #a5d6a7; background: #f9fbe7; }
.add-cell { padding: 6px 8px !important; }

/* Стили для справочника кодов часов */
.code-row { transition: background-color 0.2s ease; }
.code-row:hover { background-color: #f5f5f5 !important; }
.code-row .v-btn { opacity: 1 !important; transition: transform 0.2s ease, background-color 0.2s ease; }
.code-row .v-btn:hover { transform: scale(1.15); background-color: rgba(0, 0, 0, 0.04) !important; }

/* Принудительное применение стилей выпадающего списка поиска сотрудников
   (дублируем переопределение через :deep() — на случай, если часть DOM
   рендерится внутри scoped-области компонента). */
:deep(.v-autocomplete .v-list-item),
:deep(.v-select .v-list-item),
:deep(.v-menu .v-overlay__content .v-list-item) {
  --v-hover-opacity: rgba(255, 243, 224, 1) !important;
  --v-focus-opacity: rgba(255, 243, 224, 1) !important;
  --v-activated-opacity: rgba(255, 224, 178, 1) !important;
  --v-selected-opacity: rgba(255, 224, 178, 1) !important;
  --v-pressed-opacity: rgba(255, 204, 128, 1) !important;
  background-color: #ffffff !important;
  color: #212121 !important;
  transition: background-color 0.15s ease, color 0.15s ease;
}
:deep(.v-autocomplete .v-list-item > .v-list-item__overlay),
:deep(.v-select .v-list-item > .v-list-item__overlay),
:deep(.v-menu .v-overlay__content .v-list-item > .v-list-item__overlay) {
  background-color: transparent !important;
  opacity: 0 !important;
}
:deep(.v-autocomplete .v-list-item::before),
:deep(.v-select .v-list-item::before),
:deep(.v-menu .v-overlay__content .v-list-item::before) {
  background-color: transparent !important;
  opacity: 0 !important;
}
:deep(.v-autocomplete .v-list-item:hover),
:deep(.v-select .v-list-item:hover),
:deep(.v-menu .v-overlay__content .v-list-item:hover) {
  background-color: #fff3e0 !important;
  color: #212121 !important;
}
:deep(.v-autocomplete .v-list-item:hover > .v-list-item__overlay),
:deep(.v-select .v-list-item:hover > .v-list-item__overlay),
:deep(.v-menu .v-overlay__content .v-list-item:hover > .v-list-item__overlay) {
  background-color: #fff3e0 !important;
  opacity: 1 !important;
}
:deep(.v-autocomplete .v-list-item.v-list-item--active),
:deep(.v-select .v-list-item.v-list-item--active),
:deep(.v-menu .v-overlay__content .v-list-item.v-list-item--active) {
  background-color: #ffe0b2 !important;
  color: #212121 !important;
}
:deep(.v-autocomplete .v-list-item.v-list-item--active > .v-list-item__overlay),
:deep(.v-select .v-list-item.v-list-item--active > .v-list-item__overlay),
:deep(.v-menu .v-overlay__content .v-list-item.v-list-item--active > .v-list-item__overlay) {
  background-color: #ffe0b2 !important;
  opacity: 1 !important;
}
:deep(.v-autocomplete .v-list-item-title),
:deep(.v-select .v-list-item-title) {
  color: #212121 !important;
}
:deep(.v-autocomplete .v-list-item-subtitle),
:deep(.v-select .v-list-item-subtitle) {
  color: #616161 !important;
}
/* Явный текст ФИО/табельного в слотах prepend/append v-list-item.
   Поднимаем его над слоем подсветки (.v-list-item__overlay), чтобы при
   оранжевом выделении надпись не закрашивалась и оставалась тёмной. */
.emp-search-title,
.emp-search-subtitle {
  position: relative;
  z-index: 2;
  pointer-events: none;
}
:deep(.emp-search-title) {
  color: #212121 !important;
  font-weight: 500;
}
:deep(.emp-search-subtitle) {
  color: #616161 !important;
  font-size: 0.8rem;
}
</style>

<style>
.cell-menu .v-overlay__content { background: white; border-radius: 8px; }

/* ============================================================================
   ВЫПАДАЮЩИЙ СПИСОК ПОИСКА СОТРУДНИКОВ — АГРЕССИВНОЕ ПЕРЕОПРЕДЕЛЕНИЕ СТИЛЕЙ
   БЕЗ ПРИВЯЗКИ К КЛАССУ .emp-search-item (он мог не применяться / перебиваться).

   Стилизуются ВСЕ .v-list-item внутри выпадающих меню v-autocomplete/v-select
   (контент лежит в оверлей-портале: .v-menu__content / .v-overlay__content).

   Корень «чёрного фона»: Vuetify 3 рисует hover/active-фон не на самом
   .v-list-item, а на дочернем span.v-list-item__overlay с цветом
   var(--v-hover-opacity) = rgba(0,0,0,...) (тёмный/чёрный слой поверх нашего
   цвета), плюс псевдоэлемент ::before и правила темы (.v-list-item--active —
   почти чёрный фон). Поэтому переопределяем ВСЕ слои сразу: сам элемент,
   overlay (::after), ::before, CSS-переменные состояния, детей и тёмную тему.
   ========================================================================== */

/* 1) БАЗА: фон списка всегда белый, текст тёмный, никакого чёрного.
      Переопределяем CSS-переменные состояний Vuetify на оранжевые тона. */
.v-autocomplete .v-list-item,
.v-select .v-list-item,
.v-menu .v-overlay__content .v-list-item,
.v-field__append-inner ~ * .v-list-item {
  --v-hover-opacity: rgba(255, 243, 224, 1) !important;    /* #fff3e0 */
  --v-focus-opacity: rgba(255, 243, 224, 1) !important;
  --v-activated-opacity: rgba(255, 224, 178, 1) !important; /* #ffe0b2 */
  --v-selected-opacity: rgba(255, 224, 178, 1) !important;
  --v-pressed-opacity: rgba(255, 204, 128, 1) !important;   /* #ffcc80 */
  background-color: #ffffff !important;
  color: #212121 !important;
  transition: background-color 0.15s ease, color 0.15s ease;
}

/* 2) STATE-OVERLAY Vuetify (главный источник чёрного): в покое полностью скрыт */
.v-autocomplete .v-list-item > .v-list-item__overlay,
.v-select .v-list-item > .v-list-item__overlay,
.v-menu .v-overlay__content .v-list-item > .v-list-item__overlay {
  background-color: transparent !important;
  opacity: 0 !important;
  transition: opacity 0.15s ease, background-color 0.15s ease;
}

/* 3) PSEDOELEMENT ::before (старый hover-слой): в покое скрыт */
.v-autocomplete .v-list-item::before,
.v-select .v-list-item::before,
.v-menu .v-overlay__content .v-list-item::before {
  background-color: transparent !important;
  opacity: 0 !important;
}

/* 4) HOVER мышью — очень светло-оранжевый (#fff3e0), текст остаётся тёмным */
.v-autocomplete .v-list-item:hover,
.v-select .v-list-item:hover,
.v-menu .v-overlay__content .v-list-item:hover,
.v-menu .v-overlay__content .v-list-item:focus-visible,
.v-autocomplete .v-list-item.v-list-item--hover,
.v-select .v-list-item.v-list-item--hover {
  background-color: #fff3e0 !important;
  color: #212121 !important;
}
.v-autocomplete .v-list-item:hover > .v-list-item__overlay,
.v-select .v-list-item:hover > .v-list-item__overlay,
.v-menu .v-overlay__content .v-list-item:hover > .v-list-item__overlay,
.v-autocomplete .v-list-item.v-list-item--hover > .v-list-item__overlay,
.v-select .v-list-item.v-list-item--hover > .v-list-item__overlay {
  background-color: #fff3e0 !important;
  opacity: 1 !important;
}
.v-autocomplete .v-list-item:hover::before,
.v-select .v-list-item:hover::before,
.v-menu .v-overlay__content .v-list-item:hover::before {
  background-color: #fff3e0 !important;
  opacity: 1 !important;
}

/* 5) НАВИГАЦИЯ КЛАВИШАМИ ВВЕРХ/ВНИЗ (активный элемент) — оранжевый (#ffe0b2).
      Специфичность заведомо выше правил темы (.v-list-item--active). */
.v-autocomplete .v-list-item.v-list-item--active,
.v-select .v-list-item.v-list-item--active,
.v-menu .v-overlay__content .v-list-item.v-list-item--active,
.v-select .v-list-item.v-list-item--selected,
.v-autocomplete .v-list-item[aria-selected="true"] {
  background-color: #ffe0b2 !important;
  color: #212121 !important;
}
.v-autocomplete .v-list-item.v-list-item--active > .v-list-item__overlay,
.v-select .v-list-item.v-list-item--active > .v-list-item__overlay,
.v-menu .v-overlay__content .v-list-item.v-list-item--active > .v-list-item__overlay,
.v-select .v-list-item.v-list-item--selected > .v-list-item__overlay {
  background-color: #ffe0b2 !important;
  opacity: 1 !important;
}

/* Активный + под курсором — amber-200 (#ffcc80) */
.v-autocomplete .v-list-item.v-list-item--active:hover,
.v-select .v-list-item.v-list-item--active:hover,
.v-menu .v-overlay__content .v-list-item.v-list-item--active:hover {
  background-color: #ffcc80 !important;
  color: #212121 !important;
}
.v-autocomplete .v-list-item.v-list-item--active:hover > .v-list-item__overlay,
.v-select .v-list-item.v-list-item--active:hover > .v-list-item__overlay,
.v-menu .v-overlay__content .v-list-item.v-list-item--active:hover > .v-list-item__overlay {
  background-color: #ffcc80 !important;
  opacity: 1 !important;
}

/* 6) ДОЧЕРНИЕ ЭЛЕМЕНТЫ (span, title, subtitle, prepend/append) — без тёмного
      фона, текст тёмный, подзаголовок чуть светлее, но читаемый */
.v-autocomplete .v-list-item > *:not(.v-list-item__overlay),
.v-select .v-list-item > *:not(.v-list-item__overlay),
.v-menu .v-overlay__content .v-list-item > *:not(.v-list-item__overlay) {
  background-color: transparent !important;
  color: inherit !important;
}
.v-autocomplete .v-list-item-title,
.v-select .v-list-item-title,
.v-menu .v-overlay__content .v-list-item-title {
  color: #212121 !important;
}
.v-autocomplete .v-list-item-subtitle,
.v-select .v-list-item-subtitle,
.v-menu .v-overlay__content .v-list-item-subtitle {
  color: #616161 !important;
}

/* 6b) Явный текст ФИО/табельного (span.emp-search-title / .emp-search-subtitle
        в слотах prepend/append) — тёмный и ПОВЕРХ слоя подсветки. Без этого при
        оранжевом выделении active-элемента надпись закрашивалась и сливалась
        с фоном («просто оранжевое окно»). */
.v-autocomplete .v-list-item .emp-search-title,
.v-select .v-list-item .emp-search-title,
.v-menu .v-overlay__content .v-list-item .emp-search-title {
  position: relative;
  z-index: 2;
  color: #212121 !important;
  font-weight: 500;
}
.v-autocomplete .v-list-item .emp-search-subtitle,
.v-select .v-list-item .emp-search-subtitle,
.v-menu .v-overlay__content .v-list-item .emp-search-subtitle {
  position: relative;
  z-index: 2;
  color: #616161 !important;
  font-size: 0.8rem;
}
.v-autocomplete .v-list-item--active .emp-search-title,
.v-select .v-list-item--active .emp-search-title,
.v-menu .v-overlay__content .v-list-item--active .emp-search-title,
.v-autocomplete .v-list-item:hover .emp-search-title,
.v-select .v-list-item:hover .emp-search-title,
.v-menu .v-overlay__content .v-list-item:hover .emp-search-title {
  color: #212121 !important;
}

/* 7) ТЁМНАЯ ТЕМА: принудительно светлый фон/тёмный текст в списках поиска */
.v-theme--dark .v-autocomplete .v-list-item,
.v-theme--dark .v-select .v-list-item,
.v-theme--dark .v-menu .v-overlay__content .v-list-item {
  background-color: #ffffff !important;
  color: #212121 !important;
}
.v-theme--dark .v-autocomplete .v-list-item:hover,
.v-theme--dark .v-select .v-list-item:hover,
.v-theme--dark .v-menu .v-overlay__content .v-list-item:hover {
  background-color: #fff3e0 !important;
  color: #212121 !important;
}
.v-theme--dark .v-autocomplete .v-list-item.v-list-item--active,
.v-theme--dark .v-select .v-list-item.v-list-item--active,
.v-theme--dark .v-menu .v-overlay__content .v-list-item.v-list-item--active {
  background-color: #ffe0b2 !important;
  color: #212121 !important;
}
.v-theme--dark .v-autocomplete .v-list-item > .v-list-item__overlay,
.v-theme--dark .v-select .v-list-item > .v-list-item__overlay {
  background-color: transparent !important;
}
/* Сам контейнер выпадающего меню — белый, если тема попытается окрасить его */
.v-autocomplete .v-menu__content,
.v-select .v-menu__content,
.v-autocomplete .v-overlay__content,
.v-select .v-overlay__content {
  background-color: #ffffff !important;
}
.v-autocomplete .v-list,
.v-select .v-list,
.v-menu .v-overlay__content .v-list {
  background-color: #ffffff !important;
}

/* Кнопка «Очистить ячейку» в меню выбора кода — красный акцент */
.code-menu-clear :deep(.v-list-item-title),
.code-menu-clear :deep(.v-list-item__prepend .v-icon) {
  color: rgb(179, 38, 30) !important;
}
.code-menu-clear :deep(.v-list-item-title) {
  font-weight: 600;
}
</style>