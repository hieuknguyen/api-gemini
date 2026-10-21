import React, { useState, useEffect } from 'react';
import { TabType } from './types';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Header } from './components/layout/Header';
import { ChatTab } from './components/chat/ChatTab';
import { ImageGenTab } from './components/image/ImageGenTab';
import { SkillsTab } from './components/skills/SkillsTab';
import { AccountsTab } from './components/accounts/AccountsTab';
import { ApiTab } from './components/api/ApiTab';
import { AuthModal } from './components/modals/AuthModal';
import { UserProfileModal } from './components/modals/UserProfileModal';
import { PaymentModal } from './components/modals/PaymentModal';
import { skillService } from './services/skillService';
import { accountService } from './services/accountService';

const MainApp: React.FC = () => {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [selectedSkillId, setSelectedSkillId] = useState('default');
  const [skillsCount, setSkillsCount] = useState(0);
  const [accountsCount, setAccountsCount] = useState(0);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);

  // Tự động chuyển về tab 'chat' nếu không phải admin mà tab hiện tại là 'accounts'
  useEffect(() => {
    if (!isAdmin && activeTab === 'accounts') {
      setActiveTab('chat');
    }
  }, [isAdmin, activeTab]);

  useEffect(() => {
    // Fetch counts
    skillService.getSkills().then((s) => setSkillsCount(s.length)).catch(() => {});
    if (isAdmin) {
      accountService.getAccounts().then((a) => setAccountsCount(a.length)).catch(() => {});
    } else {
      setAccountsCount(0);
    }
  }, [activeTab, isAdmin]);

  const handleSelectSkillFromTab = (skillId: string) => {
    setSelectedSkillId(skillId);
    setActiveTab('chat');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* App Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        skillsCount={skillsCount}
        accountsCount={accountsCount}
        onOpenProfile={() => setIsProfileOpen(true)}
        onOpenPayment={() => setIsPaymentOpen(true)}
      />

      {/* Main Content Area (Matches templates/index.html line 290) */}
      <main className="flex-1 w-full max-w-[1720px] mx-auto px-3 sm:px-5 lg:px-6 py-2 sm:py-2.5 flex flex-col min-h-0 overflow-hidden">
        {activeTab === 'chat' && (
          <ChatTab
            selectedSkillId={selectedSkillId}
            onSkillChange={setSelectedSkillId}
          />
        )}
        {activeTab === 'images' && <ImageGenTab />}
        {activeTab === 'skills' && (
          <SkillsTab
            activeSkillId={selectedSkillId}
            onSelectSkill={handleSelectSkillFromTab}
            onNavigateToApi={() => setActiveTab('api')}
          />
        )}
        {activeTab === 'accounts' && isAdmin && <AccountsTab />}
        {activeTab === 'api' && <ApiTab />}
      </main>

      {/* Modals */}
      <AuthModal />
      <UserProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        onOpenPayment={() => setIsPaymentOpen(true)}
      />
      <PaymentModal
        isOpen={isPaymentOpen}
        onClose={() => setIsPaymentOpen(false)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
