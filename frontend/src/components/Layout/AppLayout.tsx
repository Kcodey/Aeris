import React from 'react'

interface AppLayoutProps {
  children: React.ReactNode
  onLogout: () => void
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return <div>{children}</div>
}

export default AppLayout
