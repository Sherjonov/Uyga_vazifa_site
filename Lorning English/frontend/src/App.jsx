import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import { PageLoader } from './components/Loader';
import { homeFor } from './utils/format';

const Login = lazy(() => import('./pages/auth/Login'));
const Register = lazy(() => import('./pages/auth/Register'));
const VerifyOTP = lazy(() => import('./pages/auth/VerifyOTP'));
const Onboarding = lazy(() => import('./pages/auth/Onboarding'));
const JoinGroup = lazy(() => import('./pages/auth/JoinGroup'));

const StudentHome = lazy(() => import('./pages/student/Home'));
const Homework = lazy(() => import('./pages/student/Homework'));
const Tests = lazy(() => import('./pages/student/Tests'));
const TestRun = lazy(() => import('./pages/student/TestRun'));
const StudentRating = lazy(() => import('./pages/student/Rating'));
const ScoreHistory = lazy(() => import('./pages/student/History'));
const UztozAI = lazy(() => import('./pages/student/UztozAI'));
const StudentSettings = lazy(() => import('./pages/student/Settings'));
const ContactTeacher = lazy(() => import('./pages/student/ContactTeacher'));
const Profile = lazy(() => import('./pages/student/Profile'));
const StudentVocab = lazy(() => import('./pages/student/Vocab'));
const StudentBooks = lazy(() => import('./pages/student/Books'));
const StudentExtra = lazy(() => import('./pages/student/Extra'));
const TBooks = lazy(() => import('./pages/teacher/Books'));
const TVocabResults = lazy(() => import('./pages/teacher/VocabResults'));
const AddExtra = lazy(() => import('./pages/teacher/AddExtra'));

const TStudents = lazy(() => import('./pages/teacher/Students'));
const TStudentProfile = lazy(() => import('./pages/teacher/StudentProfile'));
const TGrid = lazy(() => import('./pages/teacher/Grid'));
const TDanger = lazy(() => import('./pages/teacher/DangerZone'));
const TSettings = lazy(() => import('./pages/teacher/Settings'));
const AddHomework = lazy(() => import('./pages/teacher/AddHomework'));
const AddTest = lazy(() => import('./pages/teacher/AddTest'));
const RetakeRequests = lazy(() => import('./pages/teacher/RetakeRequests'));
const Review = lazy(() => import('./pages/teacher/Review'));
const TRating = lazy(() => import('./pages/teacher/Rating'));
const TMessages = lazy(() => import('./pages/teacher/Messages'));
const TParents = lazy(() => import('./pages/teacher/ParentMessages'));
const Help = lazy(() => import('./pages/teacher/Help'));

/** Faqat tizimga kirmagan foydalanuvchilar uchun sahifalar */
function GuestOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (user) return <Navigate to={homeFor(user)} replace />;
  return children;
}

/** Kirgan foydalanuvchi + rol tekshiruvi */
function Protected({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />;
  return children;
}

function OnboardingGate() {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.onboarded) return <Navigate to={homeFor(user)} replace />;
  return <Onboarding />;
}

function Root() {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  return <Navigate to={homeFor(user)} replace />;
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Root />} />
        <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
        <Route path="/verify" element={<GuestOnly><VerifyOTP /></GuestOnly>} />
        <Route path="/onboarding" element={<OnboardingGate />} />
        <Route path="/join" element={<Protected role="student"><JoinGroup /></Protected>} />

        <Route path="/student" element={<Protected role="student"><Layout /></Protected>}>
          <Route index element={<Navigate to="home" replace />} />
          <Route path="home" element={<StudentHome />} />
          <Route path="homework" element={<Homework />} />
          <Route path="vocab" element={<StudentVocab />} />
          <Route path="books" element={<StudentBooks />} />
          <Route path="extra" element={<StudentExtra />} />
          <Route path="tests" element={<Tests />} />
          <Route path="tests/:id/run" element={<TestRun />} />
          <Route path="rating" element={<StudentRating />} />
          <Route path="history" element={<ScoreHistory />} />
          <Route path="uztoz-ai" element={<UztozAI />} />
          <Route path="profile" element={<Profile />} />
          <Route path="settings" element={<StudentSettings />} />
          <Route path="contact" element={<ContactTeacher />} />
        </Route>

        <Route path="/teacher" element={<Protected role="teacher"><Layout /></Protected>}>
          <Route index element={<Navigate to="students" replace />} />
          <Route path="students" element={<TStudents />} />
          <Route path="students/:studentId" element={<TStudentProfile />} />
          <Route path="grid" element={<TGrid />} />
          <Route path="danger-zone" element={<TDanger />} />
          <Route path="settings" element={<TSettings />} />
          <Route path="homework" element={<AddHomework />} />
          <Route path="tests" element={<AddTest />} />
          <Route path="books" element={<TBooks />} />
          <Route path="vocab-results" element={<TVocabResults />} />
          <Route path="extra" element={<AddExtra />} />
          <Route path="retake" element={<RetakeRequests />} />
          <Route path="review" element={<Review />} />
          <Route path="rating" element={<TRating />} />
          <Route path="messages" element={<TMessages />} />
          <Route path="parents" element={<TParents />} />
          <Route path="help" element={<Help />} />
        </Route>

        <Route path="*" element={<Root />} />
      </Routes>
    </Suspense>
  );
}
