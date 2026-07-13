import streamlit as st
from supabase import create_client, Client

# [필수] 내 Supabase 프로젝트 주소와 anon key를 적어주세요!
SUPABASE_URL = "https://kktrkhfpxeavhaugzohd.supabase.co"
SUPABASE_KEY = "sb_publishable_c0dtskcvaF1CjK9fZwBm-g_XgRg6hXH"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="스마트 오답노트 관리자", layout="wide")

# 탭 기능으로 화면 분할 (채점 기능 / 정답 등록 기능)
tab1, tab2 = st.tabs(["📝 모의고사 채점하기", "⚙️ 새 시험지 정답 등록하기"])

# ==========================================
# 탭 1: 모의고사 채점 및 취약점 분석
# ==========================================
with tab1:
    st.title("📊 취약점 분석 스마트 오답노트")
    st.caption("실시간으로 채점하고, 내가 어떤 개념 단원에 취약한지 차트로 분석해 줍니다.")

    with st.sidebar:
        st.header("⚙️ 시험지 설정")
        exam_id = st.text_input("시험 ID 입력", value="2026_03_MATH")

    st.subheader("✍️ 내 답안 마킹 (1번 ~ 20번)")
    user_answers = {}

    for row in range(5):
        cols = st.columns(4)
        for col_idx in range(4):
            q_num = row * 4 + col_idx + 1
            with cols[col_idx]:
                user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}", value="")

    st.divider()

    if st.button("🚀 전 문항 일괄 채점 및 분석하기", type="primary"):
        with st.spinner("클라우드 DB 조회 및 채점 중..."):
            try:
                res = supabase.table("questions").select("*").eq("exam_id", exam_id).execute()
                questions = res.data
                
                if not questions:
                    st.error("입력하신 시험 ID 정보가 없습니다. 먼저 정답 등록 탭에서 정답을 입력해주세요.")
                else:
                    wrong_questions = []
                    correct_count = 0
                    
                    notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id).execute()
                    saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
                    
                    questions.sort(key=lambda x: x["question_number"])
                    
                    for q in questions:
                        q_num_str = str(q["question_number"])
                        user_ans = user_answers.get(q_num_str, "").strip()
                        correct_ans = str(q["answer"]).strip()
                        
                        if user_ans == correct_ans:
                            correct_count += 1
                        else:
                            wrong_questions.append({
                                "question_number": q["question_number"],
                                "correct_answer": correct_ans,
                                "user_answer": user_ans if user_ans else "(미제출)",
                                "concept_tags": q.get("concept_tags", []),
                                "saved_memo": saved_memos.get(q_num_str, "")
                            })
                    
                    total_questions = len(questions)
                    score_str = f"{correct_count}/{total_questions}"
                    wrong_count = len(wrong_questions)
                    
                    st.success(f"💯 채점 완료! 내 성적: {score_str}")
                    
                    if wrong_count == 0:
                        st.balloons()
                        st.info("와우! 만점입니다! 🎉")
                    else:
                        tag_counts = {}
                        for item in wrong_questions:
                            for tag in item['concept_tags']:
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                        
                        if tag_counts:
                            st.subheader("📊 내 취약 개념 통계 분석")
                            st.bar_chart(tag_counts, horizontal=True)
                        
                        st.divider()
                        st.subheader(f"❌ 틀린 문제 오답 노트 ({wrong_count}문항)")
                        
                        for item in wrong_questions:
                            with st.container(border=True):
                                st.markdown(f"### ❓ {item['question_number']}번 문제")
                                st.markdown(f"**🏷️ 출제 개념:** {', '.join(item['concept_tags']) if item['concept_tags'] else '지정 없음'}")
                                st.error(f"내가 제출한 답: {item['user_answer']}  |  **실제 정답: {item['correct_answer']}**")
                                
                                user_memo = st.text_area("오답 메모", value=item['saved_memo'], key=f"input_{exam_id}_{item['question_number']}")
                                if st.button("💾 DB에 영구 저장하기", key=f"btn_{exam_id}_{item['question_number']}"):
                                    save_data = {"exam_id": exam_id, "question_number": item['question_number'], "user_memo": user_memo}
                                    supabase.table("wrong_notes").upsert(save_data, on_conflict="exam_id,question_number").execute()
                                    st.toast(f"🎉 {item['question_number']}번 오답 메모 저장 완료!")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ==========================================
# 탭 2: 노가다 방지용 [자동 정답 등록기]
# ==========================================
with tab2:
    st.title("⚙️ 모의고사 정답 초고속 등록기")
    st.caption("새로운 모의고사 정답표를 한 줄로 넣으면 DB에 자동으로 20문제가 생성됩니다.")

    col1, col2, col3, col4 = st.columns(4)
    with col1: reg_year = st.number_input("년도", value=2026, step=1)
    with col2: reg_month = st.number_input("월", value=3, step=1)
    with col3: reg_grade = st.selectbox("학년", ["고1", "고2", "고3"], index=2)
    with col4: reg_subject = st.text_input("과목", value="MATH")

    # 예: 2026_03_MATH 자동 생성
    reg_exam_id = f"{reg_year}_{str(reg_month).zfill(2)}_{reg_subject}"
    st.info(f"등록될 시험 ID: **{reg_exam_id}**")

    st.subheader("📋 정답 일괄 입력")
    # 사용자가 정답지 보고 숫자만 쭉 치는 칸 (예: 3 5 2 1 4...)
    raw_answers = st.text_input("1번부터 20번까지의 정답을 띄어쓰기(공백)로 구분해서 입력하세요.", value="3 5 2 1 4 2 3 5 1 4 2 3 5 1 3 4 2 5 3 1")

    st.subheader("🏷️ 단원 개념 태그 입력 (선택사항)")
    raw_tags = st.text_area("각 문제의 개념 태그를 쉼표(,)로 구분해서 20개 적어주세요. (귀찮으면 생략 가능, 기본값으로 세팅됨)", 
                           value="행렬,수열,방정식,미분,적분,함수,기하,확률,통계,로그,지수,삼각함수,수열의극한,함수의극한,미분,적분,벡터,순열,조합,정규분포")

    if st.button("🔥 클릭 한 번으로 DB에 20문항 원클릭 등록", type="primary"):
        # 입력받은 텍스트 파싱
        ans_list = raw_answers.strip().split()
        tag_list = [t.strip() for t in raw_tags.strip().split(",")]
        
        if len(ans_list) != 20:
            st.error(f"정답 개수가 {len(ans_list)}개입니다. 정확히 20개를 입력해주세요!")
        else:
            with st.spinner("Supabase DB에 정답지 굽는 중..."):
                try:
                    bulk_data = []
                    for i in range(20):
                        # 태그가 부족하면 '미지정'으로 처리
                        tag = [tag_list[i]] if i < len(tag_list) and tag_list[i] else ["미지정"]
                        
                        row_data = {
                            "year": reg_year,
                            "month": reg_month,
                            "grade": reg_grade,
                            "subject": reg_subject,
                            "exam_id": reg_exam_id,
                            "question_number": i + 1,
                            "answer": ans_list[i],
                            "concept_tags": tag
                        }
                        bulk_data.append(row_data)
                    
                    # Supabase에 한방에 다 집어넣기!
                    supabase.table("questions").insert(bulk_data).execute()
                    st.balloons()
                    st.success(f"🎉 {reg_exam_id} 시험지 20문항 정답 등록이 완료되었습니다! 이제 바로 채점할 수 있습니다.")
                except Exception as e:
                    st.error(f"등록 실패 (이미 등록된 시험지일 수 있습니다): {e}")