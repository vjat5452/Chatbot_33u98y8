import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import { useAuth } from './contexts/AuthContext'
import { Loader2 } from 'lucide-react'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Leads = lazy(() => import('./pages/Leads'))
const LeadView = lazy(() => import('./pages/LeadView'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Conversations = lazy(() => import('./pages/Conversations'))
const Issues = lazy(() => import('./pages/Issues'))
const GoldenQA = lazy(() => import('./pages/GoldenQA'))
const Data = lazy(() => import('./pages/Data'))
const Settings = lazy(() => import('./pages/Settings'))
const EmailCampaigns = lazy(() => import('./pages/email/EmailCampaigns'))
const EmailCampaignCreate = lazy(() => import('./pages/email/EmailCampaignCreate'))
const EmailCampaignView = lazy(() => import('./pages/email/EmailCampaignView'))
const EmailTemplates = lazy(() => import('./pages/email/EmailTemplates'))
const EmailContacts = lazy(() => import('./pages/email/EmailContacts'))
const EmailSequences = lazy(() => import('./pages/email/EmailSequences'))
const EmailAnalytics = lazy(() => import('./pages/email/EmailAnalytics'))
const EmailDirectSend = lazy(() => import('./pages/email/EmailDirectSend'))
const WhatsAppConversations = lazy(() => import('./pages/whatsapp/WhatsAppConversations'))
const WhatsAppChat = lazy(() => import('./pages/whatsapp/WhatsAppChat'))
const WhatsAppAnalytics = lazy(() => import('./pages/whatsapp/WhatsAppAnalytics'))

function Loading() {
  return (
    <div className="flex items-center justify-center py-20 text-muted-foreground">
      <div className="text-center">
        <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
        Loading...
      </div>
    </div>
  )
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-center text-gray-500">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
        <p className="text-sm">Checking session...</p>
      </div>
    </div>
  )
}

export default function App() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <FullScreenLoader />

  if (!isAuthenticated) return <Login />

  return (
    <Layout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/leads/:id" element={<LeadView />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/golden-qa" element={<GoldenQA />} />
          <Route path="/data" element={<Data />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/email" element={<EmailCampaigns />} />
          <Route path="/email/create" element={<EmailCampaignCreate />} />
          <Route path="/email/:id" element={<EmailCampaignView />} />
          <Route path="/email/templates" element={<EmailTemplates />} />
          <Route path="/email/contacts" element={<EmailContacts />} />
          <Route path="/email/sequences" element={<EmailSequences />} />
          <Route path="/email/send" element={<EmailDirectSend />} />
          <Route path="/email/analytics" element={<EmailAnalytics />} />
          <Route path="/whatsapp" element={<WhatsAppConversations />} />
          <Route path="/whatsapp/analytics" element={<WhatsAppAnalytics />} />
          <Route path="/whatsapp/:sessionId" element={<WhatsAppChat />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
