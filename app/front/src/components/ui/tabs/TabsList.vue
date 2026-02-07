<script setup lang="ts">
import { cn } from "@/lib/utils";
import { TabsList, type TabsListProps } from "radix-vue";
import { computed, type HTMLAttributes } from "vue";

const props = defineProps<TabsListProps & { class?: HTMLAttributes["class"] }>();

const delegatedProps = computed(() => {
  const { class: _className, ...delegated } = props;
  void _className;
  return delegated;
});
</script>

<template>
  <TabsList
    v-bind="delegatedProps"
    :class="
      cn(
        'inline-flex h-12 items-center justify-center rounded-lg bg-muted p-1.5 text-muted-foreground gap-1',
        props.class,
      )
    "
  >
    <slot />
  </TabsList>
</template>
