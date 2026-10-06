<script setup lang="ts">
import { computed } from 'vue'

/**
 * 滚动数字。
 *
 * 输入是「已经格式化好的文本」（如 "22.60"、"同比 ↑12.8%"、"8.14"），组件把其中
 * 每个数字字符渲染成一条 0-9 的竖直滚轮，数值变化时用 CSS transform 平滑滚动到位；
 * 小数点、波浪号、单位、箭头、百分号等非数字字符按静态文本原样输出。
 *
 * 两个刻意的设计：
 * - 滚轮自上而下排 9→0，所以数值变大时轨道向下位移，观感就是「数字向下滚」。
 * - 每列固定 1ch 宽，滚动过程中不会因为当前数字的宽度变化把整行推来推去。
 *
 * 组件只负责渲染层，不感知业务含义，也不做取整/单位换算 —— 那些仍由调用方决定。
 */
const props = withDefaults(
  defineProps<{
    /** 已格式化的文本；null / undefined / 空串走 fallback */
    text: string | number | null | undefined
    /** 空值占位符 */
    fallback?: string
  }>(),
  { fallback: '-' },
)

/** 轨道内容：自上而下 9 → 0。 */
const TRACK = ['9', '8', '7', '6', '5', '4', '3', '2', '1', '0']

const cells = computed(() => {
  const raw = props.text
  const str = raw === null || raw === undefined || raw === '' ? props.fallback : String(raw)
  const chars = str.split('')
  const len = chars.length
  return chars.map((ch, i) => {
    const digit = ch >= '0' && ch <= '9'
    return {
      // 从右往左编号：低位 key 稳定。数值跨数量级（9.99 → 10.01）时
      // 复用已有节点，只有真正新出现的高位才新建，避免整行重建把动画打断。
      key: `k${len - 1 - i}`,
      ch,
      digit,
      // 要显示数字 d，轨道需上移 (9 - d) 行
      offset: digit ? Number(ch) - 9 : 0,
    }
  })
})
</script>

<template>
  <span class="rn">
    <template v-for="c in cells" :key="c.key">
      <span v-if="c.digit" class="rn-col">
        <span class="rn-track" :style="{ transform: `translateY(${c.offset}em)` }">
          <i v-for="d in TRACK" :key="d">{{ d }}</i>
        </span>
      </span>
      <span v-else class="rn-lit">{{ c.ch }}</span>
    </template>
  </span>
</template>

<style scoped>
.rn {
  display: inline-flex;
  align-items: flex-end;
  /* 滚轮窗口的底边即元素的 baseline，这里补一点下沉，
     让它和相邻的单位文字（元/kg、万吨、%）落在同一条视觉基线上 */
  vertical-align: -0.16em;
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}

.rn-col,
.rn-lit {
  display: block;
  height: 1em;
  line-height: 1em;
}

/* 只有滚轮需要裁切；标点/箭头不裁，否则 ↑ 这类高字符会被切掉上半截 */
.rn-col {
  width: 1ch;
  text-align: center;
  overflow: hidden;
}

.rn-lit {
  overflow: visible;
}

.rn-track {
  display: block;
  /* 必须明显短于滚动周期（约 0.55~0.9s）：每格滚到位后要留出静止时间。
     过渡时长一旦接近或超过更新间隔，数字就会永远停在大两格之间，
     看起来是重影而不是滚动。曲线取「先快后慢」，像滚轮被拨动后缓停。 */
  transition: transform 0.28s cubic-bezier(0.2, 0.9, 0.3, 1);
  will-change: transform;
}

.rn-track i {
  display: block;
  height: 1em;
  line-height: 1em;
  font-style: normal;
}
</style>
