import React, { useState, useEffect } from 'react';
import { Skill } from '../../types';
import { skillService } from '../../services/skillService';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { SkillModal } from './SkillModal';
import {
  Sparkles,
  Copy,
  Check,
  Edit2,
  CheckCircle2,
  FileCode,
  Loader2
} from 'lucide-react';

interface SkillsTabProps {
  activeSkillId: string;
  onSelectSkill: (skillId: string) => void;
  onNavigateToApi?: () => void;
}

export const SkillsTab: React.FC<SkillsTabProps> = ({ activeSkillId, onSelectSkill, onNavigateToApi }) => {
  const { user } = useAuth();
  const { showToast } = useToast();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkillForEdit, setSelectedSkillForEdit] = useState<Skill | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchSkills = async () => {
    try {
      setLoading(true);
      const data = await skillService.getSkills();
      setSkills(data);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải danh sách kỹ năng', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  const handleCopyId = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    showToast(`Đã sao chép Skill ID: ${id}`, 'success');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleEdit = (skill: Skill, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedSkillForEdit(skill);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-5 rounded-2xl">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <span>Quản Lý Bộ Kỹ Năng (Custom Skills & API IDs)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">Kỹ năng Viết content riêng tư, chỉ tài khoản sở hữu mới xem và sử dụng được.</p>
        </div>
      </div>

      {/* Skill API Guide Banner (Matches index.html lines 691-704) */}
      {skills.length > 0 && <div className="bg-purple-950/20 border border-purple-800/40 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2.5">
          <span className="text-base">💡</span>
          <div className="text-slate-300">
            <span className="font-semibold text-purple-300">Cách gọi API kèm Skill ID:</span>
            <span> Chỉ cần bấm <b>"Copy ID"</b> trên thẻ kỹ năng và truyền vào body: </span>
            <code className="px-1.5 py-0.5 rounded bg-slate-900 text-purple-300 font-mono border border-purple-500/30">{"{\"prompt\": \"...\", \"skill_id\": \"skill_...\"}"}</code>
          </div>
        </div>
        {onNavigateToApi && (
          <button
            onClick={onNavigateToApi}
            className="px-3 py-1 bg-purple-600/30 hover:bg-purple-600 text-purple-200 hover:text-white rounded-lg transition shrink-0 font-medium border border-purple-500/30 active:scale-95"
          >
            Xem mẫu code API &rarr;
          </button>
        )}
      </div>}

      {/* Skills Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
        </div>
      ) : skills.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/40 border border-slate-800 rounded-2xl">
          <FileCode className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 text-sm font-medium">Chưa có kỹ năng nào.</p>
          <p className="text-slate-500 text-xs mt-1">Tài khoản này không sở hữu kỹ năng nào.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.map((s) => {
            const isSelected = s.id === activeSkillId;
            const isOwner = Boolean(s.is_owner || (user && s.user_id === user.id));
            const canEdit = isOwner;

            return (
              <div
                key={s.id}
                className={`bg-slate-900/60 border rounded-2xl p-5 flex flex-col justify-between space-y-4 transition group ${
                  isSelected
                    ? 'border-purple-500/50 shadow-lg shadow-purple-500/10'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
                        <Sparkles className="w-5 h-5" />
                      </span>
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <h4 className="font-bold text-sm text-white">{s.name}</h4>
                          {isOwner ? (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                              RIÊNG TƯ
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-slate-400 border border-slate-700">
                              Tùy biến
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {isSelected && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>ĐANG CHỌN</span>
                      </span>
                    )}
                  </div>

                  {/* Skill ID Bar with Copy */}
                  <div className="flex items-center justify-between bg-slate-950/90 border border-purple-500/20 rounded-xl px-3 py-1.5 text-xs">
                    <div className="flex items-center space-x-1.5 truncate">
                      <span className="text-[11px] text-slate-400 font-medium shrink-0">Skill ID:</span>
                      <code className="font-mono text-xs font-semibold text-purple-300 truncate select-all">
                        {s.id}
                      </code>
                    </div>
                    <button
                      onClick={(e) => handleCopyId(s.id, e)}
                      className="flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-purple-500/10 hover:bg-purple-600 text-purple-300 hover:text-white transition text-[11px] font-medium border border-purple-500/20 shrink-0 ml-2"
                      title="Sao chép ID"
                    >
                      {copiedId === s.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedId === s.id ? 'Đã chép' : 'Copy ID'}</span>
                    </button>
                  </div>

                  {/* System Prompt Preview */}
                  <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 text-xs font-mono text-slate-300 max-h-28 overflow-y-auto leading-relaxed select-text">
                    {s.system_prompt}
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                  <button
                    onClick={() => onSelectSkill(s.id)}
                    className={`px-3 py-1.5 rounded-lg transition font-medium flex items-center space-x-1.5 ${
                      isSelected
                        ? 'bg-purple-600 text-white shadow'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{isSelected ? 'Đang kích hoạt' : 'Dùng kỹ năng này'}</span>
                  </button>

                  <div className="flex items-center space-x-1.5">
                    {canEdit ? (
                      <button
                        onClick={(e) => handleEdit(s, e)}
                        className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition"
                        title="Chỉnh sửa kỹ năng"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      <SkillModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        skill={selectedSkillForEdit}
        onSaved={fetchSkills}
      />
    </div>
  );
};
