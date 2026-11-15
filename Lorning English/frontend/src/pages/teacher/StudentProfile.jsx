import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, BookOpenCheck, GraduationCap, KeyRound } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import ScoreHistory from '../../components/ScoreHistory';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { initials, num } from '../../utils/format';
import './teacher.css';

export default function StudentProfile() {
  const { studentId } = useParams();
  const [params, setParams] = useSearchParams();
  const { t } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: groupsLoading } = useGroups();
  const requestedGroupId = Number(params.get('group_id')) || groupId;
  const selectedGroupId = groups.some(group => group.id === requestedGroupId) ? requestedGroupId : groupId;
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [password, setPassword] = useState('');
  const [passwordBusy, setPasswordBusy] = useState(false);

  useEffect(() => {
    if (groupsLoading) return;
    if (!selectedGroupId) {
      setLoading(false);
      setError('');
      setStudent(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError('');
    api.get(`/groups/${selectedGroupId}/members`).then(({ data }) => {
      if (!active) return;
      const found = data.find(item => item.id === Number(studentId));
      if (!found) {
        setStudent(null);
        setError(t('students.profileNotFound'));
      } else {
        setStudent(found);
      }
    }).catch(err => {
      if (active) {
        setStudent(null);
        setError(errMsg(err));
      }
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [groupsLoading, selectedGroupId, studentId, t]);

  const changeGroup = id => {
    setGroupId(id);
    setParams(id ? { group_id: id } : {});
  };

  const resetPassword = async event => {
    event.preventDefault();
    if (password.length < 6) return toast.error(t('err.passwordShort'));
    setPasswordBusy(true);
    try {
      await api.put(`/roster/${studentId}/password`, { password });
      setPassword('');
      toast.success(t('students.passwordChanged'));
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setPasswordBusy(false);
    }
  };

  return (
    <div className="page page-wide">
      <PageHeader
        icon={GraduationCap}
        title={t('students.knowledge')}
        subtitle={t('students.knowledgeSubtitle')}
        actions={<Link className="btn btn-ghost" to="/teacher/students"><ArrowLeft size={16} /> {t('students.backToList')}</Link>}
      />

      <div className="student-profile-group">
        <GroupSelect groups={groups} value={selectedGroupId} onChange={changeGroup} />
      </div>

      {loading ? <SkeletonList n={3} h={90} /> : error ? (
        <div className="card"><Empty icon={GraduationCap} title={t('students.profileNotFound')} text={error} /></div>
      ) : student ? (
        <div className="stack student-profile">
          <section className="card student-profile-head">
            <div className="row">
              <span className="avatar avatar-lg">{initials(student.name)}</span>
              <div className="spacer">
                <h2>{student.name}</h2>
                <div className="hint">{student.phone || student.email || t('students.noContact')}</div>
              </div>
              <span className={`badge ${student.claimed ? 'badge-success' : 'badge-warning'}`}>
                {student.claimed ? t('students.registered') : t('students.notRegistered')}
              </span>
            </div>
            <div className="student-profile-stats">
              <div className="student-profile-stat">
                <span className="hint">{t('students.score')}</span>
                <strong className="mono">{num(student.total_score, 1)}</strong>
              </div>
              <div className="student-profile-stat">
                <span className="hint">{t('students.absences')}</span>
                <strong className="mono">{student.absences}</strong>
              </div>
            </div>
          </section>

          {student.claimed && (
            <form className="card student-password-form" onSubmit={resetPassword}>
              <div>
                <h3><KeyRound size={17} /> {t('students.changePassword')}</h3>
                <p className="hint">{t('students.passwordHint')}</p>
              </div>
              <div className="row">
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  minLength={6}
                  maxLength={72}
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  placeholder={t('settings.newPassword')}
                />
                <button className="btn btn-primary" disabled={passwordBusy || password.length < 6}>
                  {passwordBusy ? <Spinner size={15} /> : <KeyRound size={15} />}
                  {t('common.save')}
                </button>
              </div>
            </form>
          )}

          {!student.claimed && <div className="alert alert-info">{t('students.passwordUnregistered')}</div>}

          <section className="stack">
            <div className="student-knowledge-title">
              <BookOpenCheck size={21} />
              <div>
                <h2>{t('students.knowledge')}</h2>
                <p className="hint">{t('students.knowledgeSubtitle')}</p>
              </div>
            </div>
            <ScoreHistory endpoint={`/rating/students/${student.id}/history?group_id=${selectedGroupId}`} />
          </section>
        </div>
      ) : null}
    </div>
  );
}
