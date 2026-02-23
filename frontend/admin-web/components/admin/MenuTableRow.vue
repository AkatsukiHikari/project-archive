<template>
  <TableRow class="hover group">
    <TableCell class="font-medium px-4 py-3">
      <div
        class="flex items-center"
        :style="{ paddingLeft: `${level * 2}rem` }"
      >
        <div
          class="w-5 h-5 mr-2 text-muted-foreground flex items-center justify-center"
        >
          <Icon
            :name="
              node.icon ||
              (node.type === 'DIR'
                ? 'lucide:folder'
                : node.type === 'MENU'
                  ? 'lucide:file-text'
                  : 'lucide:cpu')
            "
            class="w-4 h-4"
          />
        </div>
        <span
          :class="
            level === 0 ? 'text-foreground font-bold' : 'text-foreground/80'
          "
        >
          {{ node.name }}
        </span>
      </div>
    </TableCell>
    <TableCell class="px-4 py-3">
      <span class="font-mono text-xs text-muted-foreground">{{
        node.path ? `/${node.path}` : "-"
      }}</span>
    </TableCell>
    <TableCell class="px-4 py-3">
      <Badge
        :variant="
          node.type === 'DIR'
            ? 'secondary'
            : node.type === 'MENU'
              ? 'default'
              : 'outline'
        "
        class="text-[10px] px-1.5 py-0 font-semibold"
      >
        {{
          node.type === "DIR" ? "目录" : node.type === "MENU" ? "菜单" : "按钮"
        }}
      </Badge>
    </TableCell>
    <TableCell class="px-4 py-3">
      <code
        class="font-mono text-[10px] bg-muted px-2 py-0.5 rounded border border-border text-muted-foreground whitespace-nowrap"
      >
        {{ node.code }}
      </code>
    </TableCell>
    <TableCell class="px-4 py-3">
      <span
        v-if="node.is_visible"
        class="text-green-600 text-[10px] font-semibold"
        >可见</span
      >
      <span v-else class="text-muted-foreground/50 text-[10px]">隐藏</span>
    </TableCell>
    <TableCell class="px-4 py-3 text-center">
      <div
        class="flex items-center justify-center gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <Button
          v-if="node.type !== 'BUTTON'"
          variant="ghost"
          size="sm"
          class="h-8 text-primary hover:text-primary hover:bg-primary/10 px-2"
          title="挂载子资源"
          @click="$emit('add-child', node)"
        >
          <Icon name="lucide:plus" class="w-3.5 h-3.5 mr-1" />
          注入
        </Button>
        <Button
          variant="ghost"
          size="icon"
          class="h-8 w-8 text-blue-500 hover:text-blue-600 hover:bg-blue-50"
          title="配置"
          @click="$emit('edit', node)"
        >
          <Icon name="lucide:settings" class="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          :disabled="node.is_system"
          class="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-30"
          title="销毁"
          @click="$emit('delete', node.id)"
        >
          <Icon name="lucide:trash-2" class="w-3.5 h-3.5" />
        </Button>
      </div>
    </TableCell>
  </TableRow>
  <template v-if="node.children && node.children.length > 0">
    <MenuTableRow
      v-for="child in node.children"
      :key="child.id"
      :node="child"
      :level="level + 1"
      @edit="$emit('edit', $event)"
      @add-child="$emit('add-child', $event)"
      @delete="$emit('delete', $event)"
    />
  </template>
</template>

<script setup lang="ts">
import type { MenuTree } from "~/api/iam";

defineProps<{
  node: MenuTree;
  level: number;
}>();

defineEmits(["edit", "add-child", "delete"]);
</script>
