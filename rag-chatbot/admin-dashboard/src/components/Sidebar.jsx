import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Home, Users, BarChart3, MessageSquare, AlertTriangle, Settings, ArrowLeft, Mail, FileText, Users2, GitBranch, ChevronDown, Sparkles, Send, MessageCircle, Database, LogOut } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const mainLinks = [
  { to: '/', label: 'Dashboard', icon: Home },
  { to: '/leads', label: 'Leads', icon: Users },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/conversations', label: 'Conversations', icon: MessageSquare },
  { to: '/issues', label: 'Reported Issues', icon: AlertTriangle },
  { to: '/golden-qa', label: 'Golden Q&A', icon: Sparkles },
  { to: '/data', label: 'Data', icon: Database },
]

const whatsappLinks = [
  { to: '/whatsapp', label: 'Conversations', icon: MessageCircle },
  { to: '/whatsapp/analytics', label: 'Analytics', icon: BarChart3 },
]

const emailLinks = [
  { to: '/email', label: 'Campaigns', icon: Mail },
  { to: '/email/send', label: 'Send Email', icon: Send },
  { to: '/email/templates', label: 'Templates', icon: FileText },
  { to: '/email/contacts', label: 'Contacts', icon: Users2 },
  { to: '/email/sequences', label: 'Sequences', icon: GitBranch },
  { to: '/email/analytics', label: 'Email Analytics', icon: BarChart3 },
]

function NavItem({ link }) {
  return (
    <NavLink
      to={link.to}
      end={link.to === '/' || link.to === '/email' || link.to === '/whatsapp'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 text-[13px] font-medium rounded-lg transition-all duration-150 ${
          isActive
            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
            : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
        }`
      }
    >
      <link.icon className="w-[18px] h-[18px]" />
      {link.label}
    </NavLink>
  )
}

export default function Sidebar() {
  const [emailOpen, setEmailOpen] = useState(true)
  const [whatsappOpen, setWhatsappOpen] = useState(true)
  const { logout, username } = useAuth()

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-sidebar text-sidebar-foreground flex flex-col border-r border-sidebar-border">
      {/* Brand */}
      <NavLink to="/" className="block p-6 border-b border-sidebar-border hover:bg-sidebar-accent/50 transition-colors">
        <div className="flex items-center gap-3">
          <img src={import.meta.env.BASE_URL + 'logo.png'} alt="Sparrowi" className="w-9 h-9 object-contain" />
          <h1 className="text-lg font-bold tracking-tight">Sparrowi</h1>
        </div>
      </NavLink>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-1 overflow-y-auto">
        {mainLinks.map(link => <NavItem key={link.to} link={link} />)}

        {/* Email Sales Section */}
        <div className="pt-2">
          <button
            onClick={() => setEmailOpen(!emailOpen)}
            className="flex items-center justify-between w-full px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/40 hover:text-sidebar-foreground/60 transition-colors"
          >
            Email Dashboard
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${emailOpen ? '' : '-rotate-90'}`} />
          </button>
          {emailOpen && (
            <div className="space-y-1">
              {emailLinks.map(link => <NavItem key={link.to} link={link} />)}
            </div>
          )}
        </div>

        {/* WhatsApp Section */}
        <div className="pt-2">
          <button
            onClick={() => setWhatsappOpen(!whatsappOpen)}
            className="flex items-center justify-between w-full px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/40 hover:text-sidebar-foreground/60 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              WhatsApp
            </span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${whatsappOpen ? '' : '-rotate-90'}`} />
          </button>
          {whatsappOpen && (
            <div className="space-y-1">
              {whatsappLinks.map(link => <NavItem key={link.to} link={link} />)}
            </div>
          )}
        </div>

        {/* Settings at bottom of nav */}
        <div className="pt-2">
          <NavItem link={{ to: '/settings', label: 'Settings', icon: Settings }} />
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border space-y-2">
        <a
          href="/"
          className="flex items-center gap-2 text-xs text-sidebar-foreground/40 hover:text-sidebar-foreground/70 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Website
        </a>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-xs text-sidebar-foreground/40 hover:text-red-400 transition-colors w-full"
        >
          <LogOut className="w-3.5 h-3.5" />
          Logout{username ? ` (${username})` : ''}
        </button>
      </div>
    </aside>
  )
}
