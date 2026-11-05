import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { User, Lock, Shield, RefreshCw, Eye, EyeOff, Info, MessageSquare, BarChart3, Database, Zap } from 'lucide-react'

function generateCaptcha() {
  const a = Math.floor(Math.random() * 10) + 1
  const b = Math.floor(Math.random() * 10) + 1
  return { a, b, answer: a + b }
}

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [captcha, setCaptcha] = useState(generateCaptcha)
  const [captchaInput, setCaptchaInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const refreshCaptcha = useCallback(() => {
    setCaptcha(generateCaptcha())
    setCaptchaInput('')
  }, [])

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(''), 5000)
      return () => clearTimeout(t)
    }
  }, [error])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('Please enter username and password')
      return
    }

    if (!captchaInput || parseInt(captchaInput) !== captcha.answer) {
      setError('Incorrect security verification')
      refreshCaptcha()
      return
    }

    setLoading(true)
    try {
      await login(username.trim(), password, captcha.answer, captcha.answer)
    } catch (err) {
      setError(err.message)
      refreshCaptcha()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Gray bg with centered white card */}
      <div className="w-full lg:w-[45%] flex items-center justify-center bg-[#f0f2f5] px-6 py-10">
        <div className="w-full max-w-[440px] bg-white rounded-2xl shadow-xl px-10 py-10">
          {/* Logo — centered, large */}
          <div className="text-center mb-6">
            <img
              src={import.meta.env.BASE_URL + 'sparrow-logo.png'}
              alt="Sparrow"
              className="h-12 object-contain mx-auto"
            />
          </div>

          {/* Title — centered, smaller than logo */}
          <h2 className="text-xl font-bold text-gray-900 text-center">Secure Login</h2>
          <p className="text-sm text-gray-500 text-center mb-6">Sign in to access your chatbot dashboard</p>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
                <User className="w-4 h-4 text-gray-400" />
                Username
              </label>
              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all bg-white"
                autoFocus
                autoComplete="username"
              />
            </div>

            {/* Password */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
                <Lock className="w-4 h-4 text-gray-400" />
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all pr-10 bg-white"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Security Verification */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
                <Shield className="w-4 h-4 text-gray-400" />
                Security Verification
              </label>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono font-bold text-gray-800 min-w-[100px] justify-center">
                  {captcha.a} + {captcha.b} =
                </div>
                <input
                  type="number"
                  placeholder="?"
                  value={captchaInput}
                  onChange={e => setCaptchaInput(e.target.value)}
                  className="w-20 px-3 py-2.5 rounded-lg border border-gray-300 text-sm text-center focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent bg-white"
                />
                <button
                  type="button"
                  onClick={refreshCaptcha}
                  className="p-2.5 rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 transition-colors"
                  title="New question"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Solve the equation to verify you're human
              </p>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#1e293b] text-white text-sm font-semibold rounded-lg hover:bg-[#334155] transition-colors disabled:opacity-60 disabled:cursor-wait"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Security Notice */}
          <div className="mt-5 p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <p className="flex items-center gap-2 text-sm font-semibold text-blue-700 mb-2">
              <Info className="w-4 h-4" />
              Security Notice
            </p>
            <ul className="text-xs text-blue-600 space-y-1 ml-6 list-disc">
              <li>Session expires when you close the browser</li>
              <li>Auto-logout after 30 minutes of inactivity</li>
              <li>Always logout when finished</li>
            </ul>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <p className="text-center text-xs text-gray-400">
              Sparrow Interactive &copy; {new Date().getFullYear()}. All rights reserved.
            </p>
          </div>
        </div>
      </div>

      {/* Right Panel — Dark bg with chatbot info */}
      <div className="hidden lg:flex w-[55%] bg-[#1e293b] text-white items-center justify-center px-12 py-10">
        <div className="max-w-lg">
          <h2 className="text-3xl font-bold mb-3">Welcome to Sparrowi Dashboard</h2>
          <p className="text-gray-400 text-base mb-10">
            Your all-in-one solution for managing the AI chatbot,
            leads, and business operations.
          </p>

          {/* Feature Card: Security */}
          <div className="bg-[#283548] border border-[#334155] rounded-xl p-5 mb-4">
            <div className="flex items-center gap-3 mb-3">
              <Shield className="w-5 h-5 text-white" />
              <h3 className="font-semibold text-lg">Enhanced Security</h3>
            </div>
            <ul className="space-y-2 ml-1">
              <li className="flex items-center gap-2 text-sm text-gray-300">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Session expires on browser close
              </li>
              <li className="flex items-center gap-2 text-sm text-gray-300">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Auto-logout after 30 min inactivity
              </li>
              <li className="flex items-center gap-2 text-sm text-gray-300">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                Secure encrypted connection
              </li>
            </ul>
          </div>

          {/* Feature Cards */}
          <div className="space-y-3">
            <div className="flex items-center gap-4 bg-[#283548] border border-[#334155] rounded-xl p-4">
              <div className="p-2.5 rounded-lg bg-[#334155]">
                <MessageSquare className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold">AI Chatbot Management</h3>
                <p className="text-sm text-gray-400">Monitor conversations, golden Q&A, and chatbot knowledge</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-[#283548] border border-[#334155] rounded-xl p-4">
              <div className="p-2.5 rounded-lg bg-[#334155]">
                <BarChart3 className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold">Lead Tracking & Analytics</h3>
                <p className="text-sm text-gray-400">Track leads, scores, and engagement analytics</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-[#283548] border border-[#334155] rounded-xl p-4">
              <div className="p-2.5 rounded-lg bg-[#334155]">
                <Database className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold">Knowledge Base Control</h3>
                <p className="text-sm text-gray-400">Upload PDFs, manage data sources, and refresh content</p>
              </div>
            </div>

            <div className="flex items-center gap-4 bg-[#283548] border border-[#334155] rounded-xl p-4">
              <div className="p-2.5 rounded-lg bg-[#334155]">
                <Zap className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <h3 className="font-semibold">Email & WhatsApp Campaigns</h3>
                <p className="text-sm text-gray-400">Automate outreach with email sequences and WhatsApp</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
