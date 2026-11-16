import type { Register, ThemeSetArgs } from 'claude-code'

import { makeColors } from './make-colors.js'
import { SCENE } from './scene.js'

// Night market: deep navy surfaces with white text, to sit with the navy top of the sunset sky.
const { theme, problems } = makeColors({
  label: 'Market night',
  only: 'dark',
  roles: { accent: '#8fa8ff', danger: '#ff6b6b', success: '#5cc98a', warning: '#f2c452', pro: '#c39bff' },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#0f1630',
        'surface-1': '#151d3b',
        'surface-2': '#1b2446',
        'surface-3': '#212a4f',
        'text-primary': '#f4f3fb',
        'text-secondary': '#cfd2e6',
        'text-muted': '#a5abc8',
      },
    },
  },
})

const LOOK: ThemeSetArgs = {
  colors: theme,
  backdrop: { scene: 'market', glass: { blur: 6, opacity: 0.45 } },
}

export const register: Register = on => {
  // A new session can set the theme before the app's window has attached; setting it
  // again on the first prompt makes sure the backdrop reaches the window.
  let isSetAgain = false

  on('session.start', async ($, e, next) => {
    const unpainted = problems.find(line => line.startsWith("Desktop won't paint"))

    if (unpainted !== undefined) {
      $.ui.toast(unpainted)
    }
    await $.theme.set(LOOK)

    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    if (!isSetAgain) {
      isSetAgain = true
      await $.theme.set(LOOK)
    }

    return next(e)
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') {
      return next(e)
    }
    const { Svg } = $.ui.resolve(e)

    return (
      <Svg
        source={SCENE}
        alt="A dot-art Christmas market square drawn in orange-to-yellow dots over a navy-to-sunset sky, with lights twinkling on the tree, the Ferris wheel and the garlands, and falling snow"
        isInteractive
      />
    )
  })
}
