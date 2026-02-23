<template>
  <TableRow class="hover group">
    <TableCell class="font-medium px-4 py-3">
      <div
        class="flex items-center"
        :style="{ paddingLeft: `${level * 2}rem` }"
      >
        <div
          class="w-4 h-4 mr-2 text-muted-foreground flex items-center justify-center"
          :class="node.children?.length ? '' : 'invisible'"
        >
          <Icon
            v-if="node.children?.length"
            name="lucide:folder-open"
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
      <code
        class="text-xs bg-muted px-2 py-1 rounded-sm text-muted-foreground"
        >{{ node.code }}</code
      >
    </TableCell>
    <TableCell class="text-muted-foreground text-sm px-4 py-3">
      {{ node.sort_order }}
    </TableCell>
    <TableCell class="px-4 py-3 text-center">
      <div
        class="flex items-center justify-center gap-1 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <Button
          variant="ghost"
          size="sm"
          class="h-8 text-primary hover:text-primary hover:bg-primary/10"
          title="添加子部门"
          @click="$emit('add-child', node)"
        >
          <Icon name="lucide:plus" class="w-4 h-4 mr-1" />
          子项
        </Button>
        <Button
          variant="ghost"
          size="icon"
          class="h-8 w-8 text-blue-500 hover:text-blue-600 hover:bg-blue-50"
          title="编辑"
          @click="$emit('edit', node)"
        >
          <Icon name="lucide:edit" class="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          class="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
          title="删除"
          @click="$emit('delete', node.id)"
        >
          <Icon name="lucide:trash-2" class="w-4 h-4" />
        </Button>
      </div>
    </TableCell>
  </TableRow>
  <template v-if="node.children && node.children.length > 0">
    <OrgTableRow
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
import type { OrganizationTree } from "~/api/iam";
// Note: Nuxt automatically resolves recursive components by their filename

defineProps<{
  node: OrganizationTree;
  level: number;
}>();

defineEmits(["edit", "add-child", "delete"]);
</script>
