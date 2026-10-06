import chinaRaw from '@/assets/map/china.json?raw'
import ganzhouRaw from '@/assets/map/ganzhou.json?raw'
import { echarts } from '@/utils/echarts'

const chinaGeo = JSON.parse(chinaRaw)
const ganzhouGeo = JSON.parse(ganzhouRaw)

let done = false

/** 注册中国与赣州市地图（数据来源：国家标准行政区划边界 GeoJSON，含台湾省/港澳/南海诸岛）。 */
export function registerMaps() {
  if (done) return
  if (!echarts) throw new Error('echarts global not loaded')
  echarts.registerMap('china', chinaGeo as unknown as Parameters<typeof echarts.registerMap>[1])
  echarts.registerMap('ganzhou', ganzhouGeo as unknown as Parameters<typeof echarts.registerMap>[1])
  done = true
}

export const GANZHOU_CENTER: [number, number] = [114.93, 25.83]
