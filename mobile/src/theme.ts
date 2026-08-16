export const themes = {
  sage: {
    background: '#f8f3eb',
    surface: '#fffdf8',
    text: '#19352b',
    muted: '#66756c',
    primary: '#426b57',
    accent: '#dc8f73',
    border: '#d8dfd2',
  },
  night: {
    background: '#0f211b',
    surface: '#19362c',
    text: '#f5efe5',
    muted: '#b6c8bc',
    primary: '#a8c995',
    accent: '#ef9b82',
    border: '#365447',
  },
  purple: {
    background: '#171124',
    surface: '#25183a',
    text: '#f6efff',
    muted: '#cbbddc',
    primary: '#c59be8',
    accent: '#f2a3c1',
    border: '#513c6b',
  },
  crimson: {
    background: '#211316',
    surface: '#382025',
    text: '#fff1ec',
    muted: '#d5b4b7',
    primary: '#ea8e8e',
    accent: '#f5c275',
    border: '#684047',
  },
} as const

export type ThemeName = keyof typeof themes
export type ThemeColors = (typeof themes)[ThemeName]

export const themeNames: ThemeName[] = ['sage', 'night', 'purple', 'crimson']
