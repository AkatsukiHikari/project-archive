<template>
  <div class="h-full flex flex-col bg-base-100 p-6 rounded-2xl shadow-sm">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1
          class="text-2xl font-bold text-base-content flex items-center gap-2"
        >
          <Icon name="heroicons:calendar-days" class="w-8 h-8 text-primary" />
          全景日程中心
        </h1>
        <p class="text-base-content/60 text-sm mt-1">
          管理您的会议、任务与系统事件，支持联调协作
        </p>
      </div>
      <button
        class="btn btn-primary rounded-full shadow-sm"
        @click="openCreateEvent"
      >
        <Icon name="heroicons:plus" class="w-5 h-5 mr-1" />
        新建日程
      </button>
    </div>

    <!-- Calendar Container -->
    <div
      class="flex-1 bg-base-200/30 rounded-xl border border-base-content/5 overflow-hidden"
    >
      <client-only>
        <vue-cal
          active-view="week"
          :events="mappedEvents"
          class="vuecal--blue-theme custom-full-cal"
          style="min-height: 600px"
          locale="zh-cn"
          :time-from="8 * 60"
          :time-to="20 * 60"
          :time-step="30"
          :time-cell-height="45"
          :disable-views="['years', 'year']"
          @event-click="onEventClick"
        >
          <!-- Using Vue-cal native event display for correct resizing/dragging support -->
        </vue-cal>
      </client-only>
    </div>

    <!-- Event Dialog (View/Edit/Create) -->
    <dialog
      id="event_modal"
      class="modal"
      :class="{ 'modal-open': isModalOpen }"
    >
      <div class="modal-box max-w-md p-0 overflow-hidden shadow-2xl relative">
        <div
          v-if="loading"
          class="absolute inset-0 bg-base-100/50 z-[100] flex items-center justify-center backdrop-blur-sm"
        >
          <span class="loading loading-spinner text-primary loading-lg"></span>
        </div>

        <!-- View Mode (Google Calendar Style) -->
        <div
          v-if="modalState === 'view'"
          class="bg-base-100 relative group/view"
        >
          <!-- 头部操作条 -->
          <div
            class="flex justify-end p-2 bg-base-100 absolute top-0 w-full z-10 transition-opacity opacity-0 group-hover/view:opacity-100"
          >
            <div
              class="flex items-center gap-0.5 shadow-sm rounded-lg border border-base-content/10 bg-base-100 px-1 py-1"
            >
              <button
                class="btn btn-xs btn-ghost btn-square text-base-content/70 hover:text-info"
                @click="modalState = 'edit'"
                title="编辑日程"
              >
                <Icon name="heroicons:pencil" class="w-4 h-4" />
              </button>
              <button
                class="btn btn-xs btn-ghost btn-square text-base-content/70 hover:text-error"
                @click="deleteEvent"
                title="删除日程"
              >
                <Icon name="heroicons:trash" class="w-4 h-4" />
              </button>
              <div
                class="divider divider-horizontal mx-0 w-2 h-4 my-auto"
              ></div>
              <button
                class="btn btn-xs btn-ghost btn-square text-base-content/70 hover:text-base-content"
                @click="closeModal"
                title="关闭"
              >
                <Icon name="heroicons:x-mark" class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div class="p-6 pt-12">
            <div class="flex gap-4">
              <!-- 左侧图标位 -->
              <div class="mt-1.5 shrink-0">
                <div
                  class="w-4 h-4 rounded-md bg-primary shadow-sm shadow-primary/20"
                ></div>
              </div>
              <!-- 右侧详情 -->
              <div class="flex-1 space-y-5">
                <div>
                  <h2 class="text-xl font-bold text-base-content leading-tight">
                    {{ form.title }}
                  </h2>
                  <div
                    class="text-[13px] text-base-content/70 mt-1.5 font-medium"
                  >
                    {{
                      new Date(form.start_time).toLocaleDateString("zh-CN", {
                        weekday: "long",
                        month: "long",
                        day: "numeric",
                      })
                    }}
                    ⋅ {{ form.start_time.substring(11, 16) }} –
                    {{ form.end_time.substring(11, 16) }}
                  </div>
                </div>

                <div
                  class="flex items-start gap-3"
                  v-if="form.participant_ids.length > 0"
                >
                  <Icon
                    name="heroicons:users"
                    class="w-5 h-5 text-base-content/40 mt-0.5 shrink-0"
                  />
                  <div class="flex-1">
                    <div class="text-sm font-medium text-base-content mb-2">
                      {{ form.participant_ids.length }} 位参与者
                    </div>
                    <div class="flex flex-col gap-2">
                      <div
                        v-for="ui in form.participant_ids"
                        :key="ui"
                        class="flex items-center gap-2"
                      >
                        <div
                          class="avatar"
                          v-if="allUsers.find((u) => u.id === ui)?.avatar"
                        >
                          <div
                            class="w-7 rounded-full border border-base-content/10"
                          >
                            <img
                              :src="allUsers.find((u) => u.id === ui)?.avatar"
                            />
                          </div>
                        </div>
                        <div class="avatar placeholder" v-else>
                          <div
                            class="bg-base-300 text-base-content rounded-full w-7 border border-base-content/10"
                          >
                            <span class="text-xs">{{
                              (
                                allUsers.find((u) => u.id === ui)?.full_name ||
                                allUsers.find((u) => u.id === ui)?.username ||
                                "?"
                              )
                                .charAt(0)
                                .toUpperCase()
                            }}</span>
                          </div>
                        </div>
                        <div class="flex flex-col">
                          <span
                            class="text-xs font-semibold text-base-content"
                            >{{
                              allUsers.find((u) => u.id === ui)?.full_name ||
                              allUsers.find((u) => u.id === ui)?.username
                            }}</span
                          >
                          <span class="text-[10px] text-base-content/50">{{
                            allUsers.find((u) => u.id === ui)?.email
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-3" v-if="form.location">
                  <Icon
                    name="heroicons:map-pin"
                    class="w-5 h-5 text-base-content/40 shrink-0"
                  />
                  <div class="text-sm text-base-content/90 font-medium">
                    {{ form.location }}
                  </div>
                </div>

                <div class="flex items-start gap-3" v-if="form.description">
                  <Icon
                    name="heroicons:bars-3-bottom-left"
                    class="w-5 h-5 text-base-content/40 mt-0.5 shrink-0"
                  />
                  <div
                    class="text-[13px] text-base-content/80 whitespace-pre-wrap leading-relaxed"
                  >
                    {{ form.description }}
                  </div>
                </div>
              </div>
            </div>

            <div
              class="modal-action absolute top-0 right-0 p-4 opacity-100 md:opacity-0 transition-opacity"
              style="margin-top: 0"
            >
              <button
                class="btn btn-sm btn-circle bg-base-100 shadow-sm md:hidden"
                @click="closeModal"
              >
                <Icon name="heroicons:x-mark" class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Create/Edit Form Mode -->
        <div v-else class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h3 class="font-bold text-lg">
              {{ modalState === "edit" ? "编辑日程" : "新建日程" }}
            </h3>
            <button
              class="btn btn-sm btn-circle btn-ghost"
              @click="
                modalState === 'edit' ? (modalState = 'view') : closeModal()
              "
            >
              <Icon name="heroicons:x-mark" class="w-5 h-5" />
            </button>
          </div>

          <form class="space-y-4" @submit.prevent="saveEvent">
            <div class="form-control w-full">
              <input
                v-model="form.title"
                type="text"
                required
                placeholder="添加标题"
                class="input input-bordered w-full text-lg font-medium border-base-content/20 focus:border-primary h-12"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="form-control w-full">
                <label class="label pb-1"
                  ><span
                    class="label-text text-xs font-medium text-base-content/60"
                    >开始日期和时间</span
                  ></label
                >
                <input
                  v-model="form.start_time"
                  type="datetime-local"
                  required
                  class="input input-bordered w-full bg-base-200/50"
                />
              </div>
              <div class="form-control w-full">
                <label class="label pb-1"
                  ><span
                    class="label-text text-xs font-medium text-base-content/60"
                    >结束日期和时间</span
                  ></label
                >
                <input
                  v-model="form.end_time"
                  type="datetime-local"
                  required
                  class="input input-bordered w-full bg-base-200/50"
                />
              </div>
            </div>

            <div class="form-control w-full relative">
              <label class="label pb-1"
                ><span
                  class="label-text text-xs font-medium text-base-content/60"
                  >邀请参与者 (选填)</span
                ></label
              >
              <div class="dropdown w-full">
                <div
                  tabindex="0"
                  role="button"
                  class="input input-bordered w-full flex flex-wrap gap-2 items-center p-1.5 min-h-12 h-auto"
                >
                  <template v-if="form.participant_ids.length > 0">
                    <div
                      v-for="ui in form.participant_ids"
                      :key="ui"
                      class="badge badge-primary gap-1 pl-2 pr-1 py-3 text-xs shadow-sm"
                    >
                      {{
                        allUsers.find((u) => u.id === ui)?.full_name ||
                        allUsers.find((u) => u.id === ui)?.username
                      }}
                      <button
                        type="button"
                        class="btn btn-ghost btn-xs btn-circle ml-0.5 text-primary-content/70 hover:text-primary-content hover:bg-primary-focus"
                        @click.stop="toggleParticipant(ui)"
                      >
                        <Icon name="heroicons:x-mark" class="w-3 h-3" />
                      </button>
                    </div>
                  </template>
                  <template v-else>
                    <span class="text-base-content/40 text-sm ml-2"
                      >搜索并添加邀请人...</span
                    >
                  </template>
                </div>
                <ul
                  tabindex="0"
                  class="dropdown-content z-[1] menu p-2 shadow-xl bg-base-100 rounded-box w-full max-h-56 overflow-y-auto border border-base-content/10 mt-1"
                >
                  <li v-if="allUsers.length === 0">
                    <span class="text-base-content/50 px-4 py-2 text-sm"
                      >加载中...</span
                    >
                  </li>
                  <li v-for="userItem in allUsers" :key="userItem.id">
                    <a
                      @click="toggleParticipant(userItem.id)"
                      :class="{
                        'active bg-primary/10 text-primary':
                          form.participant_ids.includes(userItem.id),
                      }"
                    >
                      <div class="flex items-center gap-2 w-full">
                        <div class="avatar" v-if="userItem.avatar">
                          <div
                            class="w-6 rounded-full border border-base-content/10"
                          >
                            <img :src="userItem.avatar" />
                          </div>
                        </div>
                        <div class="avatar placeholder" v-else>
                          <div
                            class="bg-base-200 text-base-content rounded-full w-6"
                          >
                            <span class="text-xs">{{
                              (userItem.full_name || userItem.username || "?")
                                .charAt(0)
                                .toUpperCase()
                            }}</span>
                          </div>
                        </div>
                        <div class="flex-1">
                          <div class="font-semibold text-xs">
                            {{ userItem.full_name || userItem.username }}
                          </div>
                          <div class="text-[10px] opacity-60">
                            {{ userItem.email }}
                          </div>
                        </div>
                        <Icon
                          v-if="form.participant_ids.includes(userItem.id)"
                          name="heroicons:check"
                          class="w-4 h-4 text-primary"
                        />
                      </div>
                    </a>
                  </li>
                </ul>
              </div>
            </div>

            <div class="form-control w-full">
              <div class="relative flex items-center">
                <Icon
                  name="heroicons:map-pin"
                  class="w-5 h-5 text-base-content/40 absolute left-3"
                />
                <input
                  v-model="form.location"
                  type="text"
                  placeholder="添加位置"
                  class="input input-bordered w-full pl-10 h-10 bg-base-200/50"
                />
              </div>
            </div>

            <div class="form-control w-full">
              <div class="relative">
                <Icon
                  name="heroicons:bars-3-bottom-left"
                  class="w-5 h-5 text-base-content/40 absolute left-3 top-3"
                />
                <textarea
                  v-model="form.description"
                  class="textarea textarea-bordered w-full pl-10 min-h-24 bg-base-200/50 py-3"
                  placeholder="添加说明..."
                ></textarea>
              </div>
            </div>

            <div class="modal-action mt-6 pt-2">
              <button
                type="submit"
                class="btn btn-primary px-8 shadow-sm"
                :disabled="loading"
              >
                <span
                  v-if="loading"
                  class="loading loading-spinner loading-sm"
                ></span>
                保存
              </button>
            </div>
          </form>
        </div>
      </div>
      <form
        method="dialog"
        class="modal-backdrop bg-neutral/40 backdrop-blur-[2px]"
      >
        <button @click="closeModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import VueCal from "vue-cal";
import "vue-cal/dist/vuecal.css";
import { ScheduleAPI, type ScheduleEvent } from "@/api/schedule";
import { UserAPI, type User } from "@/api/iam";

definePageMeta({
  layout: "portal",
  middleware: "auth",
});

const rawEvents = ref<ScheduleEvent[]>([]);
const allUsers = ref<User[]>([]);
const isModalOpen = ref(false);
const modalState = ref<"create" | "edit" | "view">("create");
const currentEventId = ref<string>("");
const loading = ref(false);

const form = ref({
  title: "",
  description: "",
  start_time: "",
  end_time: "",
  location: "",
  participant_ids: [] as string[],
});

// 格式化数据给 vue-cal
const mappedEvents = computed(() => {
  return rawEvents.value.map((e) => ({
    ...e,
    start: new Date(e.start_time),
    end: new Date(e.end_time),
    class:
      e.event_type === "audit"
        ? "vuecal-event-custom orange-event"
        : "vuecal-event-custom blue-event",
    title: e.title,
    content: e.location
      ? `<div style="font-size: 11px; opacity: 0.8; margin-top: 4px;">📍 ${e.location}</div>`
      : "",
    deletable: false,
    resizable: true,
    draggable: true,
  }));
});

const fetchEvents = async () => {
  try {
    const res = await ScheduleAPI.list();
    rawEvents.value = res.data;
  } catch (error) {
    console.error("Failed to fetch events", error);
  }
};

const fetchUsers = async () => {
  try {
    const res = await UserAPI.list();
    allUsers.value = res.data;
  } catch (error) {
    console.error("Failed to fetch users", error);
  }
};

const formatForInput = (dateStr: string) => {
  const d = new Date(dateStr);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};

const openCreateEvent = () => {
  modalState.value = "create";
  currentEventId.value = "";

  const now = new Date();
  now.setMinutes(0, 0, 0);
  const later = new Date(now);
  later.setHours(now.getHours() + 1);

  form.value = {
    title: "",
    description: "",
    start_time: formatForInput(now.toISOString()),
    end_time: formatForInput(later.toISOString()),
    location: "",
    participant_ids: [],
  };
  isModalOpen.value = true;
};

const toggleParticipant = (userId: string) => {
  const params = form.value.participant_ids;
  const idx = params.indexOf(userId);
  if (idx > -1) {
    params.splice(idx, 1);
  } else {
    params.push(userId);
  }
};

const onEventClick = (event: ScheduleEvent, e: Event) => {
  e.stopPropagation();
  currentEventId.value = event.id;

  const original = rawEvents.value.find((r) => r.id === event.id);
  if (original) {
    form.value = {
      title: original.title,
      description: original.description || "",
      start_time: formatForInput(original.start_time),
      end_time: formatForInput(original.end_time),
      location: original.location || "",
      participant_ids: original.participants.map((p) => p.user_id),
    };
  }

  modalState.value = "view";
  isModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
};

const saveEvent = async () => {
  loading.value = true;
  try {
    const payload = {
      ...form.value,
      start_time: new Date(form.value.start_time).toISOString(),
      end_time: new Date(form.value.end_time).toISOString(),
    };

    if (modalState.value === "edit") {
      await ScheduleAPI.update(currentEventId.value, payload);
    } else {
      await ScheduleAPI.create(payload);
    }

    await fetchEvents();
    closeModal();
  } catch (error) {
    console.error("Failed to save event", error);
  } finally {
    loading.value = false;
  }
};

const deleteEvent = async () => {
  if (!confirm("确定要彻底删除该日程吗？此操作无法撤销。")) return;
  loading.value = true;
  try {
    await ScheduleAPI.delete(currentEventId.value);
    await fetchEvents();
    closeModal();
  } catch (error) {
    console.error("Failed to delete event", error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchEvents();
  fetchUsers();
});
</script>

<style>
/* Reset and polish vue-cal presentation */
.custom-full-cal .vuecal__event {
  cursor: pointer;
}
/* Native vuecal__event overrides for layout flow & Dark Mode */
.custom-full-cal .vuecal__event {
  cursor: pointer;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex !important;
  flex-direction: column !important;
  justify-content: flex-start !important;
  align-items: flex-start !important;
  padding: 4px 6px !important;
  text-align: left !important;
  overflow: hidden;
}
.custom-full-cal .vuecal__event * {
  color: inherit !important;
}
.custom-full-cal .vuecal__event-title {
  font-weight: 600 !important;
  font-size: 13px !important;
  margin-bottom: 2px !important;
  line-height: 1.2 !important;
}
.custom-full-cal .vuecal__event-time {
  font-size: 11px !important;
  font-weight: 500 !important;
  opacity: 0.9 !important;
  line-height: 1.2 !important;
}

/* Specific standard classes matching the mappedEvents */
.vuecal__event.blue-event {
  background-color: oklch(var(--p) / 0.15) !important;
  border-left: 3px solid oklch(var(--p)) !important;
  color: oklch(var(--bc)) !important;
}
.vuecal__event.orange-event {
  background-color: oklch(var(--wa) / 0.15) !important;
  border-left: 3px solid oklch(var(--wa)) !important;
  color: oklch(var(--bc)) !important;
}
.vuecal--blue-theme .vuecal__cell-events-count {
  background-color: oklch(var(--p));
}
.vuecal__title-bar {
  background-color: oklch(var(--b2)) !important;
  color: oklch(var(--bc)) !important;
}
.vuecal__menu {
  background-color: oklch(var(--b1)) !important;
  color: oklch(var(--bc)) !important;
  border-bottom: 1px solid oklch(var(--bc) / 0.1);
}
.vuecal__cell {
  background-color: oklch(var(--b1));
  border-color: oklch(var(--bc) / 0.05) !important;
}
.vuecal__time-column {
  border-right: 1px solid oklch(var(--bc) / 0.05) !important;
}
.vuecal__time-column .vuecal__time-cell {
  color: oklch(var(--bc) / 0.4);
  font-size: 12px;
}
/* hide scrollbar for clean ui */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: oklch(var(--bc) / 0.1);
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: oklch(var(--bc) / 0.2);
}
</style>
