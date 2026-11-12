import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import hu from './hu.json'
import { deviceLanguage, useSettings } from '@/store/settingsStore'

const initial = useSettings.getState().language ?? deviceLanguage()

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hu: { translation: hu } },
  lng: initial,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
})

document.documentElement.lang = initial

// Follow the language chosen in settings
useSettings.subscribe((state) => {
  const lng = state.language ?? deviceLanguage()
  if (i18n.language !== lng) {
    void i18n.changeLanguage(lng)
    document.documentElement.lang = lng
  }
})

export default i18n
